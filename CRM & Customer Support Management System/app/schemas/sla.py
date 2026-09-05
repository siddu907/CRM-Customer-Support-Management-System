from datetime import datetime

from pydantic import Field

from app.core.enums import Priority
from app.schemas.common import Schema


class SLACreate(Schema):
	priority: Priority
	response_time_hours: int = Field(gt=0, le=720)
	resolution_time_hours: int = Field(gt=0, le=720)


class SLAUpdate(Schema):
	response_time_hours: int | None = Field(default=None, gt=0, le=720)
	resolution_time_hours: int | None = Field(default=None, gt=0, le=720)


class SLAOut(Schema):
	id: int
	priority: Priority
	response_time_hours: int
	resolution_time_hours: int
	created_at: datetime
	updated_at: datetime

