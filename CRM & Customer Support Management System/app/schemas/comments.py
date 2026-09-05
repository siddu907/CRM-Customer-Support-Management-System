from datetime import datetime

from pydantic import Field

from app.schemas.common import Schema


class CommentCreate(Schema):
	content: str = Field(min_length=1, max_length=4000)


class CommentUpdate(Schema):
	content: str = Field(min_length=1, max_length=4000)


class CommentOut(Schema):
	id: int
	ticket_id: int
	user_id: int
	content: str
	created_at: datetime
	updated_at: datetime

