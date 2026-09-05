from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.user import User
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db: Session):
        super().__init__(db, Customer)

    def by_user_id(self, user_id: int) -> Customer | None:
        return self.db.scalar(select(Customer).where(Customer.user_id == user_id))

    def filtered(self, *, search: str | None, status: str | None, page: int, limit: int) -> tuple[list[Customer], int]:
        query = select(Customer).join(Customer.user).options(joinedload(Customer.user))
        if search:
            term = f"%{search.strip()}%"
            query = query.where(or_(User.full_name.ilike(term), User.email.ilike(term), Customer.company.ilike(term), Customer.phone_number.ilike(term)))
        if status:
            query = query.where(Customer.status == status)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        results = self.db.scalars(query.order_by(Customer.created_at.desc()).offset((page - 1) * limit).limit(limit)).unique().all()
        return list(results), total
