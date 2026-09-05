from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: Session):
        super().__init__(db, Category)

    def by_name(self, name: str) -> Category | None:
        return self.db.scalar(select(Category).where(func.lower(Category.name) == name.strip().lower()))

    def filtered(self, search: str | None, active_only: bool | None = None) -> list[Category]:
        query = select(Category)
        if search:
            query = query.where(Category.name.ilike(f"%{search.strip()}%"))
        if active_only is not None:
            query = query.where(Category.is_active.is_(active_only))
        return list(self.db.scalars(query.order_by(Category.name)))
