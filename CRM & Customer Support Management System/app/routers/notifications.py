from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import update

from app.core.dependencies import CurrentUser, DbSession
from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.schemas.common import Page
from app.schemas.notifications import NotificationOut
from app.utils.helpers import page_response

router = APIRouter()


@router.get("", response_model=Page)
def list_notifications(current_user: CurrentUser, db: DbSession, unread_only: bool | None = Query(default=None, description="true returns unread notifications; false returns read notifications; omit to return both"), page: int = 1, limit: int = 20):
    if page < 1 or limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="page must be positive and limit must be between 1 and 100")
    items, total = NotificationRepository(db).for_user(current_user.id, page, limit, unread_only)
    return page_response([NotificationOut.model_validate(item).model_dump() for item in items], total, page, limit)


@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, current_user: CurrentUser, db: DbSession):
    notification = NotificationRepository(db).get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can access only your own notifications")
    notification.is_read = True
    db.commit()
    return notification


@router.put("/read-all")
def mark_all_read(current_user: CurrentUser, db: DbSession):
    result = db.execute(update(Notification).where(Notification.user_id == current_user.id, Notification.is_read.is_(False)).values(is_read=True))
    db.commit()
    return {"marked_read": result.rowcount}
