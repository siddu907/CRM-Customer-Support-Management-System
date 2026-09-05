from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def active_agents(self) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role == UserRole.SUPPORT_AGENT.value, User.is_active.is_(True))))

    def admins(self) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))))

    def filtered(self, search: str | None = None, role: str | None = None, active_only: bool = False, page: int = 1, limit: int = 20) -> tuple[list[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))
        if search:
            pattern = f"%{search.strip()}%"
            condition = (User.full_name.ilike(pattern)) | (User.email.ilike(pattern))
            query = query.where(condition)
            count_query = count_query.where(condition)
        if role:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if active_only:
            query = query.where(User.is_active.is_(True))
            count_query = count_query.where(User.is_active.is_(True))
        total = self.db.scalar(count_query) or 0
        items = list(self.db.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)).all())
        return items, total
