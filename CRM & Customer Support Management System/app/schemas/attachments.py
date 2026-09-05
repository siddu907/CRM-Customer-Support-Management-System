from datetime import datetime

from app.schemas.common import Schema


class AttachmentOut(Schema):
	id: int
	ticket_id: int
	uploaded_by: int
	file_name: str
	file_path: str
	file_size: int
	content_type: str
	created_at: datetime

