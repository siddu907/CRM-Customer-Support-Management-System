from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.ticket import Ticket
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    def __init__(self, db: Session):
        super().__init__(db, Ticket)

    def by_number(self, ticket_number: str) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.ticket_number == ticket_number))

    def filtered(
        self,
        *,
        customer_id: int | None = None,
        assigned_agent_id: int | None = None,
        status: str | None = None,
        priority: str | None = None,
        category_id: int | None = None,
        search: str | None = None,
        unassigned: bool = False,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Ticket], int]:
        query = select(Ticket).options(joinedload(Ticket.customer), joinedload(Ticket.assigned_agent), joinedload(Ticket.category))
        if customer_id is not None:
            query = query.where(Ticket.customer_id == customer_id)
        if assigned_agent_id is not None:
            query = query.where(Ticket.assigned_agent_id == assigned_agent_id)
        if unassigned:
            query = query.where(Ticket.assigned_agent_id.is_(None))
        if status:
            query = query.where(Ticket.status == status)
        if priority:
            query = query.where(Ticket.priority == priority)
        if category_id:
            query = query.where(Ticket.category_id == category_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.where(or_(Ticket.subject.ilike(term), Ticket.description.ilike(term), Ticket.ticket_number.ilike(term)))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        ordering = getattr(Ticket, sort_by, Ticket.created_at)
        ordering = ordering.asc() if sort_order == "asc" else ordering.desc()
        rows = self.db.scalars(query.order_by(ordering).offset((page - 1) * limit).limit(limit)).unique().all()
        return list(rows), total

    def workload(self) -> list[tuple[int, int]]:
        query = select(Ticket.assigned_agent_id, func.count(Ticket.id)).where(Ticket.assigned_agent_id.is_not(None), Ticket.status.not_in(["closed", "cancelled"])).group_by(Ticket.assigned_agent_id)
        return list(self.db.execute(query).all())
