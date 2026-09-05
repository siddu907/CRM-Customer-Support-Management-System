from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sla import SLA
from app.repositories.base import BaseRepository


class SLARepository(BaseRepository[SLA]):
    def __init__(self, db: Session):
        super().__init__(db, SLA)

    def by_priority(self, priority: str) -> SLA | None:
        return self.db.scalar(select(SLA).where(SLA.priority == priority))
