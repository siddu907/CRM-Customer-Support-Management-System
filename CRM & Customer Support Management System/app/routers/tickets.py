from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession, require_roles
from app.core.enums import Priority, TicketStatus, UserRole
from app.models.audit_log import AuditLog
from app.schemas.common import Page
from app.schemas.tickets import TicketAssignment, TicketCreate, TicketHistoryOut, TicketOut, TicketUpdate
from app.services.ticket import TicketService
from app.utils.helpers import page_response

router = APIRouter()


def ticket_or_404(service: TicketService, ticket_id: int):
    return service.get(ticket_id)


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, tasks: BackgroundTasks, current_user: CurrentUser, db: DbSession):
    return TicketService(db).create(current_user, data, tasks)


@router.get("", response_model=Page)
def list_tickets(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category_id: int | None = Query(default=None, gt=0),
    assigned_agent_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|priority|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    filters = {"status": status_filter.value if status_filter else None, "priority": priority.value if priority else None, "category_id": category_id, "search": search, "page": page, "limit": limit, "sort_by": sort_by, "sort_order": sort_order}
    if current_user.role == UserRole.ADMIN.value and assigned_agent_id:
        filters["assigned_agent_id"] = assigned_agent_id
    items, total = TicketService(db).list_for_actor(current_user, **filters)
    return page_response([TicketOut.model_validate(item).model_dump() for item in items], total, page, limit)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, current_user: CurrentUser, db: DbSession):
    service = TicketService(db)
    ticket = ticket_or_404(service, ticket_id)
    service.can_access(ticket, current_user)
    return ticket


@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, data: TicketUpdate, tasks: BackgroundTasks, current_user: CurrentUser, db: DbSession):
    service = TicketService(db)
    return service.update(current_user, ticket_or_404(service, ticket_id), data, tasks)


@router.put("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(ticket_id: int, data: TicketAssignment, tasks: BackgroundTasks, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT))):
    service = TicketService(db)
    return service.assign(current_user, ticket_or_404(service, ticket_id), data, tasks)


@router.put("/{ticket_id}/reassign", response_model=TicketOut)
def reassign_ticket(ticket_id: int, data: TicketAssignment, tasks: BackgroundTasks, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT))):
    service = TicketService(db)
    ticket = ticket_or_404(service, ticket_id)
    if ticket.assigned_agent_id is None:
        raise HTTPException(status_code=422, detail="Use the assign endpoint for an unassigned ticket")
    return service.assign(current_user, ticket, data, tasks, allow_reassign=True)


def transition(ticket_id: int, target: TicketStatus, tasks: BackgroundTasks, current_user, db: DbSession):
    service = TicketService(db)
    return service.change_status(current_user, ticket_or_404(service, ticket_id), target.value, tasks)


@router.put("/{ticket_id}/resolve", response_model=TicketOut)
def resolve_ticket(ticket_id: int, tasks: BackgroundTasks, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), db: DbSession = None):
    return transition(ticket_id, TicketStatus.RESOLVED, tasks, current_user, db)


@router.put("/{ticket_id}/close", response_model=TicketOut)
def close_ticket(ticket_id: int, tasks: BackgroundTasks, current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), db: DbSession = None):
    return transition(ticket_id, TicketStatus.CLOSED, tasks, current_user, db)


@router.put("/{ticket_id}/cancel", response_model=TicketOut)
def cancel_ticket(ticket_id: int, tasks: BackgroundTasks, current_user: CurrentUser, db: DbSession):
    return transition(ticket_id, TicketStatus.CANCELLED, tasks, current_user, db)


