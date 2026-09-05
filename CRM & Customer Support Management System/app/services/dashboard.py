from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Priority, SLAStatus, TicketStatus, UserRole
from app.models import Customer, Ticket, User
from app.repositories.customer import CustomerRepository
from app.services.sla import ticket_sla_status
from app.utils.helpers import as_utc


def dashboard_for(db: Session, actor: User) -> dict:
    ticket_query = select(Ticket)
    if actor.role == UserRole.CUSTOMER.value:
        customer = CustomerRepository(db).by_user_id(actor.id)
        ticket_query = ticket_query.where(Ticket.customer_id == (customer.id if customer else -1))
    elif actor.role == UserRole.SUPPORT_AGENT.value:
        ticket_query = ticket_query.where(Ticket.assigned_agent_id == actor.id)
    tickets = list(db.scalars(ticket_query.order_by(Ticket.created_at.desc())).all())
    for ticket in tickets:
        ticket.sla_status = ticket_sla_status(ticket)
    status_counts = {value: sum(ticket.status == value for ticket in tickets) for value in TicketStatus}
    common_counts = {
        "open_tickets": status_counts[TicketStatus.OPEN],
        "in_progress_tickets": status_counts[TicketStatus.IN_PROGRESS],
        "resolved_tickets": status_counts[TicketStatus.RESOLVED],
        "closed_tickets": status_counts[TicketStatus.CLOSED],
        "critical_tickets": sum(ticket.priority == Priority.CRITICAL.value for ticket in tickets),
        "sla_breached_tickets": sum(ticket.sla_status == SLAStatus.BREACHED.value for ticket in tickets),
    }
    if actor.role == UserRole.SUPPORT_AGENT.value:
        metrics: dict[str, int | float] = {
            "assigned_tickets": len(tickets),
            "open_tickets": common_counts["open_tickets"],
            "pending_tickets": status_counts[TicketStatus.WAITING_FOR_CUSTOMER],
            "resolved_tickets": common_counts["resolved_tickets"],
            "critical_tickets": common_counts["critical_tickets"],
            "sla_breached_tickets": common_counts["sla_breached_tickets"],
        }
    elif actor.role == UserRole.ADMIN.value:
        resolution_seconds = [(as_utc(ticket.resolved_at) - as_utc(ticket.created_at)).total_seconds() for ticket in tickets if ticket.resolved_at]
        metrics = {
            "total_customers": db.scalar(select(func.count(Customer.id))) or 0,
            "total_support_agents": db.scalar(select(func.count(User.id)).where(User.role == UserRole.SUPPORT_AGENT.value)) or 0,
            "total_tickets": len(tickets),
            **common_counts,
            "average_resolution_time": round(sum(resolution_seconds) / len(resolution_seconds) / 3600, 2) if resolution_seconds else 0,
        }
    else:
        metrics = {
            "total_tickets": len(tickets),
            "open_tickets": common_counts["open_tickets"],
            "in_progress_tickets": common_counts["in_progress_tickets"],
            "resolved_tickets": common_counts["resolved_tickets"],
            "closed_tickets": common_counts["closed_tickets"],
        }
    return {"metrics": metrics, "recent_tickets": tickets[:10]}