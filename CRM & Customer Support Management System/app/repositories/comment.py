from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, db: Session):
        super().__init__(db, Comment)

    def for_ticket(self, ticket_id: int) -> list[Comment]:
        return list(self.db.scalars(select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at)))
