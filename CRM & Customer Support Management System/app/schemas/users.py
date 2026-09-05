from datetime import datetime

from pydantic import Field, field_serializer, field_validator

from app.core.enums import UserRole
from app.schemas.common import Schema


class UserCreate(Schema):
	full_name: str = Field(min_length=2, max_length=100)
	email: str = Field(min_length=5, max_length=255)
	password: str = Field(min_length=8, max_length=128)
	phone_number: str | None = Field(default=None, max_length=30)
	company: str | None = Field(default=None, max_length=150)
	address: str | None = Field(default=None, max_length=500)
	role: UserRole
	is_active: bool = True

	@field_validator("role", mode="before")
	@classmethod
	def normalize_role(cls, value: str | UserRole) -> UserRole:
		if isinstance(value, str):
			for role in UserRole:
				if value.lower() in {role.name.lower(), role.value.lower(), role.value.replace(" ", "_").lower()}:
					return role
		raise ValueError("Invalid user role")


class UserUpdate(Schema):
	full_name: str | None = Field(default=None, min_length=2, max_length=100)
	is_active: bool | None = None
	role: UserRole | None = None


class UserOut(Schema):
	id: int
	full_name: str
	email: str
	role: UserRole
	is_active: bool
	created_at: datetime

	@field_serializer("role")
	def serialize_role(self, value: UserRole) -> str:
		return value.value.replace(" ", "_").lower()

