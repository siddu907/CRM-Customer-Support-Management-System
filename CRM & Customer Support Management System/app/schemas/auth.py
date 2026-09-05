from pydantic import Field, field_validator

from app.schemas.common import Schema, validate_phone_number
from app.schemas.users import UserOut


class RegisterRequest(Schema):
	full_name: str = Field(min_length=2, max_length=100)
	email: str = Field(min_length=5, max_length=255)
	password: str = Field(min_length=8, max_length=128)
	phone_number: str | None = Field(default=None, max_length=30)
	company: str | None = Field(default=None, max_length=150)
	address: str | None = Field(default=None, max_length=500)

	@field_validator("email")
	@classmethod
	def normalized_email(cls, value: str) -> str:
		value = value.strip().lower()
		if "@" not in value or value.startswith("@") or value.endswith("@"):
			raise ValueError("A valid email address is required")
		return value

	@field_validator("phone_number")
	@classmethod
	def valid_phone_number(cls, value: str | None) -> str | None:
		return validate_phone_number(value)


class LoginRequest(Schema):
	email: str = Field(default="admin@gmail.com", min_length=5, max_length=255)
	password: str = Field(default="ChangeMe123", min_length=1, max_length=128)


class TokenResponse(Schema):
	access_token: str
	token_type: str = "bearer"
	user: UserOut


class ChangePasswordRequest(Schema):
	current_password: str = Field(min_length=1, max_length=128)
	new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdate(Schema):
	full_name: str | None = Field(default=None, min_length=2, max_length=100)
	phone_number: str | None = Field(default=None, max_length=30)
	company: str | None = Field(default=None, max_length=150)
	address: str | None = Field(default=None, max_length=500)

	@field_validator("phone_number")
	@classmethod
	def valid_phone_number(cls, value: str | None) -> str | None:
		return validate_phone_number(value)

