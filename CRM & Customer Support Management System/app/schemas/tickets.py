from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.enums import Priority, SLAStatus, TicketStatus
from app.schemas.common import Schema


class TicketCreate(Schema):
	customer_id: int | None = Field(default=None, gt=0)
	category_id: int = Field(gt=0)
	subject: str = Field(min_length=3, max_length=200)
	description: str = Field(min_length=3, max_length=5000)
	priority: Priority = Priority.MEDIUM


class TicketUpdate(Schema):
	category_id: int | None = Field(default=None, gt=0)
	subject: str | None = Field(default=None, min_length=3, max_length=200)
	description: str | None = Field(default=None, min_length=3, max_length=5000)
	priority: Priority | None = None
	status: TicketStatus | None = None


class TicketAssignment(Schema):
	assigned_agent_id: int = Field(gt=0)


class TicketOut(Schema):
	id: int
	ticket_number: str
	customer_id: int
	assigned_agent_id: int | None
	category_id: int
	subject: str
	description: str
	status: TicketStatus
	priority: Priority
	sla_deadline: datetime
	first_response_at: datetime | None
	resolved_at: datetime | None
	closed_at: datetime | None
	cancelled_at: datetime | None
	sla_status: SLAStatus
	created_at: datetime
	updated_at: datetime


class TicketHistoryOut(Schema):
	id: int
	action: str
	previous_value: dict[str, Any] | None
	new_value: dict[str, Any] | None
	description: str | None
	created_at: datetime
	user_id: int | None

