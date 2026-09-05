import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User
from app.services.sla import ensure_default_slas


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python scripts/seed_admin.py <email> <password> <full_name>")
    email, password, full_name = sys.argv[1].strip().lower(), sys.argv[2], sys.argv[3].strip()
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("A user with that email already exists.")
        db.add(User(full_name=full_name, email=email, password_hash=hash_password(password), role=UserRole.ADMIN.value))
        db.commit()
        ensure_default_slas(db)
        print(f"Administrator {email} created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
