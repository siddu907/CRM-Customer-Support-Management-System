from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: Session):
        super().__init__(db, Notification)

    def for_user(self, user_id: int, page: int, limit: int, unread_only: bool | None) -> tuple[list[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only is not None:
            query = query.where(Notification.is_read.is_(not unread_only))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.db.scalars(query.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
        return list(rows), total
