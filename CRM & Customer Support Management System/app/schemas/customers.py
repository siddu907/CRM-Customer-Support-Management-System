from datetime import datetime

from pydantic import Field, field_validator

from app.core.enums import CustomerStatus
from app.schemas.auth import RegisterRequest
from app.schemas.common import Schema, validate_phone_number


class CustomerCreate(RegisterRequest):
	status: CustomerStatus = CustomerStatus.ACTIVE


class CustomerUpdate(Schema):
	full_name: str | None = Field(default=None, min_length=2, max_length=100)
	phone_number: str | None = Field(default=None, max_length=30)
	company: str | None = Field(default=None, max_length=150)
	address: str | None = Field(default=None, max_length=500)
	status: CustomerStatus | None = None

	@field_validator("phone_number")
	@classmethod
	def valid_phone_number(cls, value: str | None) -> str | None:
		return validate_phone_number(value)


class CustomerOut(Schema):
	id: int
	user_id: int
	full_name: str
	email: str
	phone_number: str | None
	company: str | None
	address: str | None
	status: CustomerStatus
	created_at: datetime

