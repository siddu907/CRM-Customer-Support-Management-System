from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")


def forbidden(detail: str = "You do not have permission to perform this action") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def page_response(items: list, total: int, page: int, limit: int) -> dict:
    return {"items": items, "meta": {"page": page, "limit": limit, "total": total, "pages": ceil(total / limit) if total else 0}}
