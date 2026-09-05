import re
from typing import Any

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def validate_phone_number(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or not re.fullmatch(r"\+?[0-9][0-9 ()-]{5,28}[0-9]", value):
        raise ValueError("Phone number must contain only numbers and optional +, spaces, parentheses, or hyphens")
    return value


class PageMeta(Schema):
    page: int
    limit: int
    total: int
    pages: int


class Page(Schema):
    items: list[Any]
    meta: PageMeta
