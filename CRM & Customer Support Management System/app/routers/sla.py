from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession, require_roles
from app.core.enums import SLAStatus, UserRole
from app.models.ticket import Ticket
from app.schemas.common import Page
from app.schemas.tickets import TicketOut
from app.services.ticket import refresh_sla
from app.utils.helpers import page_response

router = APIRouter()


def sla_ticket_page(db: DbSession, current_user, wanted: SLAStatus | None, page: int, limit: int):
    query = select(Ticket)
    if current_user.role == UserRole.SUPPORT_AGENT.value:
        query = query.where(Ticket.assigned_agent_id == current_user.id)
    tickets = list(db.scalars(query.order_by(Ticket.sla_deadline)).all())
    for ticket in tickets:
        refresh_sla(ticket)
    db.commit()
    if wanted:
        tickets = [ticket for ticket in tickets if ticket.sla_status == wanted.value]
    total = len(tickets)
    rows = tickets[(page - 1) * limit : page * limit]
    return page_response([TicketOut.model_validate(ticket).model_dump() for ticket in rows], total, page, limit)


@router.get("/tickets", response_model=Page)
def sla_tickets(current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), db: DbSession = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return sla_ticket_page(db, current_user, None, page, limit)


@router.get("/breached", response_model=Page)
def breached_tickets(current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), db: DbSession = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return sla_ticket_page(db, current_user, SLAStatus.BREACHED, page, limit)


@router.get("/at-risk", response_model=Page)
def at_risk_tickets(current_user=Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT)), db: DbSession = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return sla_ticket_page(db, current_user, SLAStatus.AT_RISK, page, limit)
