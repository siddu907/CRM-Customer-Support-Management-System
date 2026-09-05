from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Customer, User
from app.repositories.customer import CustomerRepository
from app.repositories.user import UserRepository
from app.schemas.auth import ProfileUpdate
from app.schemas.users import UserCreate, UserUpdate
from app.services.audit_log import audit
from app.utils.helpers import conflict


class AuthService:
	def __init__(self, db: Session):
		self.db = db
		self.users = UserRepository(db)
		self.customers = CustomerRepository(db)

	def register_customer(self, payload) -> User:
		if self.users.by_email(payload.email):
			raise conflict("An account with this email already exists")
		user = self.users.add(User(full_name=payload.full_name.strip(), email=payload.email.lower(), password_hash=hash_password(payload.password), role=UserRole.CUSTOMER.value))
		self.customers.add(Customer(user_id=user.id, phone_number=payload.phone_number, company=payload.company, address=payload.address))
		audit(self.db, user.id, "customer_registered", "user", user.id, new={"email": user.email, "role": user.role})
		self.db.commit()
		self.db.refresh(user)
		return user

	def login(self, email: str, password: str) -> tuple[str, User]:
		user = self.users.by_email(email.strip().lower())
		if not user or not verify_password(password, user.password_hash):
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
		if not user.is_active:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is inactive")
		return create_access_token({"sub": str(user.id), "role": user.role}), user

	def change_password(self, user: User, current_password: str, new_password: str) -> None:
		if not verify_password(current_password, user.password_hash):
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
		user.password_hash = hash_password(new_password)
		audit(self.db, user.id, "password_changed", "user", user.id)
		self.db.commit()

	def update_profile(self, user: User, payload: ProfileUpdate) -> User:
		values = payload.model_dump(exclude_unset=True)
		if "full_name" in values:
			user.full_name = values.pop("full_name")
		if values:
			customer = self.customers.by_user_id(user.id)
			if customer:
				for field, value in values.items():
					setattr(customer, field, value)
		audit(self.db, user.id, "profile_updated", "user", user.id, new=payload.model_dump(exclude_unset=True))
		self.db.commit()
		self.db.refresh(user)
		return user

	def create_user(self, actor: User, payload: UserCreate) -> User:
		if self.users.by_email(payload.email):
			raise conflict("An account with this email already exists")
		user = self.users.add(User(full_name=payload.full_name.strip(), email=payload.email.lower(), password_hash=hash_password(payload.password), role=payload.role.value, is_active=payload.is_active))
		if payload.role == UserRole.CUSTOMER:
			self.customers.add(Customer(user_id=user.id, phone_number=payload.phone_number, company=payload.company, address=payload.address))
		audit(self.db, actor.id, "user_created", "user", user.id, new={"email": user.email, "role": user.role})
		self.db.commit()
		return user

	def update_user(self, actor: User, user: User, payload: UserUpdate) -> User:
		before = {"full_name": user.full_name, "role": user.role, "is_active": user.is_active}
		values = payload.model_dump(exclude_unset=True)
		requested_role = values.get("role", user.role)
		for field, value in values.items():
			setattr(user, field, value.value if hasattr(value, "value") else value)
		if user.customer and "is_active" in values:
			user.customer.status = "active" if user.is_active else "inactive"
		audit(self.db, actor.id, "user_updated", "user", user.id, previous=before, new={"full_name": user.full_name, "role": user.role, "is_active": user.is_active})
		self.db.commit()
		return user

