from datetime import datetime

from app.schemas.common import Schema


class NotificationOut(Schema):
	id: int
	user_id: int
	ticket_id: int | None
	event_type: str
	message: str
	is_read: bool
	created_at: datetime

