from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import DbSession, require_roles
from app.core.enums import UserRole
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_logs import AuditLogOut
from app.schemas.common import Page
from app.utils.helpers import page_response

router = APIRouter()


@router.get("", response_model=Page)
def list_audit_logs(db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN)), entity_type: str | None = None, user_id: int | None = Query(default=None, gt=0), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    items, total = AuditLogRepository(db).filtered(entity_type, user_id, page, limit)
    return page_response([AuditLogOut.model_validate(item).model_dump() for item in items], total, page, limit)


@router.get("/{log_id}", response_model=AuditLogOut)
def get_audit_log(log_id: int, db: DbSession, current_user=Depends(require_roles(UserRole.ADMIN))):
    record = AuditLogRepository(db).get(log_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return record
