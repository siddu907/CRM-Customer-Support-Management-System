from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import Priority, SLAStatus, TicketStatus
from app.models import SLA, Ticket, User
from app.repositories.sla import SLARepository
from app.schemas.sla import SLACreate, SLAUpdate
from app.services.audit_log import audit
from app.utils.helpers import as_utc, conflict, utcnow


DEFAULT_SLAS: dict[str, tuple[int, int]] = {
	Priority.LOW.value: (48, 48),
	Priority.MEDIUM.value: (24, 24),
	Priority.HIGH.value: (8, 8),
	Priority.CRITICAL.value: (2, 2),
}


def ensure_default_slas(db: Session) -> None:
	repo = SLARepository(db)
	changed = False
	for priority, (response, resolution) in DEFAULT_SLAS.items():
		if not repo.by_priority(priority):
			repo.add(SLA(priority=priority, response_time_hours=response, resolution_time_hours=resolution))
			changed = True
	if changed:
		db.commit()


def ticket_sla_status(ticket: Ticket, now: datetime | None = None) -> str:
	now = now or utcnow()
	if ticket.first_response_at is None and now > as_utc(ticket.sla_response_deadline):
		return SLAStatus.BREACHED.value
	terminal = {TicketStatus.CLOSED.value, TicketStatus.CANCELLED.value}
	if ticket.first_response_at is None and ticket.status not in terminal | {TicketStatus.RESOLVED.value} and as_utc(ticket.sla_response_deadline) - now <= timedelta(minutes=settings.sla_at_risk_minutes):
		return SLAStatus.AT_RISK.value
	deadline = as_utc(ticket.sla_deadline)
	comparison = as_utc(ticket.resolved_at) if ticket.resolved_at else now
	if comparison > deadline:
		return SLAStatus.BREACHED.value
	if ticket.status not in terminal | {TicketStatus.RESOLVED.value} and deadline - now <= timedelta(minutes=settings.sla_at_risk_minutes):
		return SLAStatus.AT_RISK.value
	return SLAStatus.WITHIN_SLA.value


class SLAService:
	def __init__(self, db: Session):
		self.db = db
		self.repo = SLARepository(db)

	def create(self, actor: User, payload: SLACreate) -> SLA:
		if self.repo.by_priority(payload.priority.value):
			raise conflict("An SLA policy for this priority already exists")
		policy = self.repo.add(SLA(priority=payload.priority.value, response_time_hours=payload.response_time_hours, resolution_time_hours=payload.resolution_time_hours))
		audit(self.db, actor.id, "sla_created", "sla", policy.id, new={"priority": policy.priority})
		self.db.commit()
		return policy

	def update(self, actor: User, policy: SLA, payload: SLAUpdate) -> SLA:
		before = {"response_time_hours": policy.response_time_hours, "resolution_time_hours": policy.resolution_time_hours}
		for field, value in payload.model_dump(exclude_unset=True).items():
			setattr(policy, field, value)
		audit(self.db, actor.id, "sla_updated", "sla", policy.id, previous=before, new={"response_time_hours": policy.response_time_hours, "resolution_time_hours": policy.resolution_time_hours})
		self.db.commit()
		return policy

