from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Ticket, User
from app.repositories.category import CategoryRepository
from app.schemas.categories import CategoryCreate, CategoryUpdate
from app.services.audit_log import audit
from app.utils.helpers import conflict


class CategoryService:
	def __init__(self, db: Session):
		self.db = db
		self.repo = CategoryRepository(db)

	def create(self, actor: User, payload: CategoryCreate) -> Category:
		if self.repo.by_name(payload.name):
			raise conflict("A category with this name already exists")
		category = self.repo.add(Category(name=payload.name, description=payload.description, is_active=payload.status == "active"))
		audit(self.db, actor.id, "category_created", "category", category.id, new={"name": category.name})
		self.db.commit()
		return category

	def update(self, actor: User, category: Category, payload: CategoryUpdate) -> Category:
		values = payload.model_dump(exclude_unset=True)
		if "name" in values:
			duplicate = self.repo.by_name(values["name"])
			if duplicate and duplicate.id != category.id:
				raise conflict("A category with this name already exists")
		before = {"name": category.name, "status": category.status}
		for field, value in values.items():
			if field == "status":
				category.is_active = value == "active"
			else:
				setattr(category, field, value)
		audit(self.db, actor.id, "category_updated", "category", category.id, previous=before, new={"name": category.name, "status": category.status})
		self.db.commit()
		return category

	def delete(self, actor: User, category: Category) -> None:
		if self.db.scalar(select(func.count(Ticket.id)).where(Ticket.category_id == category.id)):
			raise conflict("A category with ticket history cannot be deleted; deactivate it instead")
		audit(self.db, actor.id, "category_deleted", "category", category.id)
		self.db.delete(category)
		self.db.commit()

