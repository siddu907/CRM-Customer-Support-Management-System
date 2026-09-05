from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, db: Session):
        super().__init__(db, Attachment)

    def for_ticket(self, ticket_id: int) -> list[Attachment]:
        return list(self.db.scalars(select(Attachment).where(Attachment.ticket_id == ticket_id).order_by(Attachment.created_at.desc())))
