from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import hash_password
from app.models import Customer, Ticket, User
from app.repositories.customer import CustomerRepository
from app.repositories.user import UserRepository
from app.schemas.customers import CustomerCreate, CustomerUpdate
from app.services.audit_log import audit
from app.utils.helpers import conflict


class CustomerService:
	def __init__(self, db: Session):
		self.db = db
		self.repo = CustomerRepository(db)
		self.users = UserRepository(db)

	def create(self, actor: User, payload: CustomerCreate) -> Customer:
		if self.users.by_email(payload.email):
			raise conflict("An account with this email already exists")
		user = self.users.add(User(full_name=payload.full_name.strip(), email=payload.email.lower(), password_hash=hash_password(payload.password), role=UserRole.CUSTOMER.value))
		customer = self.repo.add(Customer(user_id=user.id, phone_number=payload.phone_number, company=payload.company, address=payload.address, status=payload.status.value))
		audit(self.db, actor.id, "customer_created", "customer", customer.id, new={"email": user.email})
		self.db.commit()
		self.db.refresh(customer)
		return customer

	def update(self, actor: User, customer: Customer, payload: CustomerUpdate) -> Customer:
		before = {"full_name": customer.user.full_name, "status": customer.status, "company": customer.company}
		values = payload.model_dump(exclude_unset=True)
		if "full_name" in values:
			customer.user.full_name = values.pop("full_name")
		for field, value in values.items():
			setattr(customer, field, value.value if hasattr(value, "value") else value)
		if "status" in values:
			customer.user.is_active = customer.status == "active"
		audit(self.db, actor.id, "customer_updated", "customer", customer.id, previous=before, new={"full_name": customer.user.full_name, "status": customer.status, "company": customer.company})
		self.db.commit()
		return customer

	def delete(self, actor: User, customer: Customer) -> None:
		customer.status = "inactive"
		customer.user.is_active = False
		audit(self.db, actor.id, "customer_deactivated", "customer", customer.id, new={"status": customer.status}, description="Customer account deactivated; support history retained")
		self.db.commit()

