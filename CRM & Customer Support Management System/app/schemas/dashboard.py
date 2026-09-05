from pydantic import Field

from app.schemas.common import Schema
from app.schemas.tickets import TicketOut


class DashboardOut(Schema):
    metrics: dict[str, int | float]
    recent_tickets: list[TicketOut] = Field(default_factory=list)