import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.enums import SLAStatus, TicketStatus
from app.models import Ticket
from app.models.user import User
from app.services.sla import ticket_sla_status
from app.core.config import settings

logger = logging.getLogger(__name__)


async def run_scheduled_jobs(stop_event: asyncio.Event) -> None:
    """Run SLA checks periodically and emit one report per UTC day."""
    report_date = datetime.now(timezone.utc).date()
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(monitor_slas)
        except Exception:
            logger.exception("Scheduled SLA monitoring failed")
        today = datetime.now(timezone.utc).date()
        if today != report_date:
            try:
                await asyncio.to_thread(send_daily_support_report)
            except Exception:
                logger.exception("Scheduled daily support report failed")
            report_date = today
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.background_job_interval_seconds)
        except TimeoutError:
            continue


def monitor_slas() -> dict[str, int]:
    """Refresh SLA state and notify administrators when a ticket newly breaches."""
    db = SessionLocal()
    try:
        tickets = list(db.scalars(select(Ticket).where(Ticket.status.not_in([TicketStatus.CLOSED.value, TicketStatus.CANCELLED.value]))).all())
        admins = list(db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True))).all())
        breached = 0
        for ticket in tickets:
            before = ticket.sla_status
            ticket.sla_status = ticket_sla_status(ticket)
            if ticket.sla_status == SLAStatus.BREACHED.value:
                breached += 1
                if before != SLAStatus.BREACHED.value:
                    from app.models.notification import Notification
                    db.add_all([Notification(user_id=admin_id, ticket_id=ticket.id, event_type="sla_breached", message=f"SLA breached for ticket {ticket.ticket_number}.") for admin_id in admins])
        db.commit()
        return {"checked": len(tickets), "breached": breached}
    finally:
        db.close()


def send_daily_support_report() -> dict[str, int]:
    """Create an in-app daily summary for active administrators."""
    db = SessionLocal()
    try:
        totals = {
            "total": db.scalar(select(func.count(Ticket.id))) or 0,
            "open": db.scalar(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN.value)) or 0,
            "in_progress": db.scalar(select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.IN_PROGRESS.value)) or 0,
            "breached": db.scalar(select(func.count(Ticket.id)).where(Ticket.sla_status == SLAStatus.BREACHED.value)) or 0,
        }
        admins = list(db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True))).all())
        from app.models.notification import Notification
        message = f"Daily support report: {totals['total']} tickets; {totals['open']} open; {totals['in_progress']} in progress; {totals['breached']} SLA breached."
        db.add_all([Notification(user_id=admin_id, ticket_id=None, event_type="daily_support_report", message=message) for admin_id in admins])
        db.commit()
        return totals
    finally:
        db.close()
