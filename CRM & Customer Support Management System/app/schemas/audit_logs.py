from datetime import datetime
from typing import Any

from app.schemas.common import Schema


class AuditLogOut(Schema):
	id: int
	user_id: int | None
	action: str
	entity_type: str
	entity_id: int | None
	previous_value: dict[str, Any] | None
	new_value: dict[str, Any] | None
	description: str | None
	created_at: datetime

