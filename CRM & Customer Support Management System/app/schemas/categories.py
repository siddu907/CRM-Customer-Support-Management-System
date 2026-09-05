from datetime import datetime

from pydantic import Field, field_validator

from app.core.enums import CustomerStatus
from app.schemas.common import Schema


class CategoryCreate(Schema):
	name: str = Field(min_length=2, max_length=100)
	description: str | None = Field(default=None, max_length=500)
	status: CustomerStatus = CustomerStatus.ACTIVE

	@field_validator("name")
	@classmethod
	def clean_name(cls, value: str) -> str:
		return value.strip()


class CategoryUpdate(Schema):
	name: str | None = Field(default=None, min_length=2, max_length=100)
	description: str | None = Field(default=None, max_length=500)
	status: CustomerStatus | None = None


class CategoryOut(Schema):
	id: int
	name: str
	description: str | None
	status: CustomerStatus
	created_at: datetime

