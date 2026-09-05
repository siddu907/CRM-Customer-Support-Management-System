from datetime import timedelta
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import Priority, TicketStatus, UserRole
from app.models import Customer, Ticket, User
from app.repositories.category import CategoryRepository
from app.repositories.customer import CustomerRepository
from app.repositories.sla import SLARepository
from app.repositories.ticket import TicketRepository
from app.repositories.user import UserRepository
from app.schemas.tickets import TicketAssignment, TicketCreate, TicketUpdate
from app.services.audit_log import audit
from app.services.notification import queue_notifications
from app.services.shared import TERMINAL_STATUSES, VALID_TRANSITIONS
from app.services.sla import DEFAULT_SLAS, ticket_sla_status
from app.utils.helpers import as_utc, conflict, forbidden, not_found, utcnow


def refresh_sla(ticket: Ticket) -> None:
    ticket.sla_status = ticket_sla_status(ticket)


class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.tickets = TicketRepository(db)
        self.customers = CustomerRepository(db)
        self.categories = CategoryRepository(db)
        self.users = UserRepository(db)
        self.slas = SLARepository(db)

    def _customer_for_create(self, actor: User, requested_id: int | None) -> Customer:
        if actor.role == UserRole.CUSTOMER.value:
            customer = self.customers.by_user_id(actor.id)
            if not customer:
                raise HTTPException(status_code=400, detail="Customer profile is missing")
            if customer.status != "active":
                raise HTTPException(status_code=403, detail="Inactive customers cannot create tickets")
            return customer
        if not requested_id:
            raise HTTPException(status_code=422, detail="customer_id is required for staff-created tickets")
        customer = self.customers.get(requested_id)
        if not customer:
            raise not_found("Customer")
        if customer.status != "active" or not customer.user.is_active:
            raise HTTPException(status_code=400, detail="Inactive customers cannot receive new tickets")
        return customer

    def get(self, ticket_id: int) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise not_found("Ticket")
        refresh_sla(ticket)
        return ticket

    def can_access(self, ticket: Ticket, actor: User, *, manage: bool = False, allow_unassigned: bool = False) -> None:
        if actor.role == UserRole.ADMIN.value:
            return
        if actor.role == UserRole.CUSTOMER.value:
            if ticket.customer.user_id != actor.id:
                raise forbidden()
            return
        if actor.role == UserRole.SUPPORT_AGENT.value:
            if allow_unassigned and ticket.assigned_agent_id is None:
                return
            if ticket.assigned_agent_id != actor.id:
                raise forbidden("Support agents can manage only their assigned tickets")
            return
        raise forbidden()

    def create(self, actor: User, payload: TicketCreate, tasks: BackgroundTasks) -> Ticket:
        customer = self._customer_for_create(actor, payload.customer_id)
        category = self.categories.get(payload.category_id)
        if not category or not category.is_active:
            raise HTTPException(status_code=400, detail="An active category is required")
        policy = self.slas.by_priority(payload.priority.value)
        response_hours, resolution_hours = (policy.response_time_hours, policy.resolution_time_hours) if policy else DEFAULT_SLAS[payload.priority.value]
        created_at = utcnow()
        ticket = self.tickets.add(Ticket(ticket_number=f"PENDING-{uuid4().hex[:16]}", customer_id=customer.id, category_id=category.id, subject=payload.subject.strip(), description=payload.description.strip(), priority=payload.priority.value, sla_response_deadline=created_at + timedelta(hours=response_hours), sla_deadline=created_at + timedelta(hours=resolution_hours)))
        ticket.ticket_number = f"TKT-{ticket.id:06d}"
        refresh_sla(ticket)
        audit(self.db, actor.id, "ticket_created", "ticket", ticket.id, new={"ticket_number": ticket.ticket_number, "priority": ticket.priority, "sla_response_hours": response_hours, "sla_resolution_hours": resolution_hours})
        self.db.commit()
        self.db.refresh(ticket)
        recipients = [customer.user_id]
        event = "ticket_created"
        message = f"Ticket {ticket.ticket_number} was created."
        if ticket.priority == Priority.CRITICAL.value:
            recipients.extend(admin.id for admin in self.users.admins())
            event = "critical_ticket_created"
            message = f"Critical ticket {ticket.ticket_number} requires attention."
        queue_notifications(tasks, recipients, ticket.id, event, message)
        return ticket

    def list_for_actor(self, actor: User, **filters) -> tuple[list[Ticket], int]:
        if actor.role == UserRole.CUSTOMER.value:
            customer = self.customers.by_user_id(actor.id)
            return self.tickets.filtered(customer_id=customer.id if customer else -1, **filters)
        if actor.role == UserRole.SUPPORT_AGENT.value:
            return self.tickets.filtered(assigned_agent_id=actor.id, **filters)
        return self.tickets.filtered(**filters)

    def update(self, actor: User, ticket: Ticket, payload: TicketUpdate, tasks: BackgroundTasks) -> Ticket:
        self.can_access(ticket, actor, manage=True)
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Closed or cancelled tickets cannot be modified")
        values = payload.model_dump(exclude_unset=True)
        requested_status = values.pop("status", None)
        if actor.role == UserRole.CUSTOMER.value and (requested_status not in (None, TicketStatus.CANCELLED.value) or "priority" in values):
            raise forbidden("Customers may only update ticket details or cancel their own tickets")
        if "category_id" in values:
            category = self.categories.get(values["category_id"])
            if not category or not category.is_active:
                raise HTTPException(status_code=400, detail="An active category is required")
        before = {"subject": ticket.subject, "priority": ticket.priority, "status": ticket.status, "category_id": ticket.category_id}
        if "priority" in values and values["priority"] != ticket.priority:
            policy = self.slas.by_priority(values["priority"])
            response_hours, resolution_hours = (policy.response_time_hours, policy.resolution_time_hours) if policy else DEFAULT_SLAS[values["priority"]]
            priority_changed_at = utcnow()
            ticket.sla_response_deadline = priority_changed_at + timedelta(hours=response_hours)
            ticket.sla_deadline = priority_changed_at + timedelta(hours=resolution_hours)
        for field, value in values.items():
            setattr(ticket, field, value.value if hasattr(value, "value") else value)
        if requested_status:
            self.change_status(actor, ticket, requested_status, tasks, commit=False)
        refresh_sla(ticket)
        audit(self.db, actor.id, "ticket_updated", "ticket", ticket.id, previous=before, new={"subject": ticket.subject, "priority": ticket.priority, "status": ticket.status, "category_id": ticket.category_id})
        self.db.commit()
        return ticket

    def change_status(self, actor: User, ticket: Ticket, target: str, tasks: BackgroundTasks, *, commit: bool = True) -> Ticket:
        self.can_access(ticket, actor, manage=True)
        target = target.value if hasattr(target, "value") else target
        if target not in VALID_TRANSITIONS.get(ticket.status, set()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Invalid ticket status transition: {ticket.status} -> {target}")
        before = ticket.status
        ticket.status = target
        now = utcnow()
        if target == TicketStatus.RESOLVED.value:
            ticket.resolved_at = now
        elif target == TicketStatus.CLOSED.value:
            ticket.closed_at = now
        elif target == TicketStatus.CANCELLED.value:
            ticket.cancelled_at = now
        elif target == TicketStatus.OPEN.value and before == TicketStatus.RESOLVED.value:
            ticket.resolved_at = None
        refresh_sla(ticket)
        audit(self.db, actor.id, "ticket_status_changed", "ticket", ticket.id, previous={"status": before}, new={"status": target}, description=f"Ticket status changed from {before} to {target}.")
        if commit:
            self.db.commit()
        recipients = [ticket.customer.user_id]
        if ticket.assigned_agent_id:
            recipients.append(ticket.assigned_agent_id)
        queue_notifications(tasks, recipients, ticket.id, f"ticket_{target}", f"Ticket {ticket.ticket_number} status changed to {target.replace('_', ' ')}.")
        return ticket

    def assign(self, actor: User, ticket: Ticket, payload: TicketAssignment, tasks: BackgroundTasks, *, allow_reassign: bool = False) -> Ticket:
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Closed or cancelled tickets cannot be assigned")
        target = self.users.get(payload.assigned_agent_id)
        if not target or target.role != UserRole.SUPPORT_AGENT.value:
            raise HTTPException(status_code=400, detail="Assigned user must be a support agent")
        if not target.is_active:
            raise HTTPException(status_code=400, detail="Inactive support agents cannot be assigned tickets")
        if ticket.assigned_agent_id == target.id:
            raise conflict(f"Ticket is already assigned to {target.full_name}")
        if ticket.assigned_agent_id is not None and actor.role == UserRole.ADMIN.value and not allow_reassign:
            raise HTTPException(status_code=422, detail="Use the reassign endpoint for an already assigned ticket")
        if actor.role == UserRole.SUPPORT_AGENT.value:
            if target.id != actor.id or ticket.assigned_agent_id is not None:
                raise forbidden("Support agents may only claim an unassigned ticket or retain their own assignment")
        elif actor.role != UserRole.ADMIN.value:
            raise forbidden()
        previous_agent_id = ticket.assigned_agent_id
        ticket.assigned_agent_id = target.id
        audit(self.db, actor.id, "ticket_reassigned" if previous_agent_id else "ticket_assigned", "ticket", ticket.id, previous={"assigned_agent_id": previous_agent_id}, new={"assigned_agent_id": target.id})
        self.db.commit()
        recipients = [ticket.customer.user_id, target.id]
        if previous_agent_id:
            recipients.append(previous_agent_id)
        queue_notifications(tasks, recipients, ticket.id, "ticket_reassigned" if previous_agent_id else "ticket_assigned", f"Ticket {ticket.ticket_number} was assigned to {target.full_name}.")
        return ticket

    def delete_or_cancel(self, actor: User, ticket: Ticket, tasks: BackgroundTasks) -> None:
        self.can_access(ticket, actor, manage=True)
        if ticket.status in TERMINAL_STATUSES:
            raise conflict("Ticket is already closed or cancelled")
        self.change_status(actor, ticket, TicketStatus.CANCELLED.value, tasks)
