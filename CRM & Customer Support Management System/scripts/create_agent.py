import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python scripts/create_agent.py <email> <password> <full_name>")

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]
    full_name = sys.argv[3].strip()

    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    if not full_name:
        raise SystemExit("Full name is required.")

    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("A user with that email already exists.")

        db.add(
            User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.SUPPORT_AGENT.value,
                is_active=True,
            )
        )
        db.commit()
        print(f"Support agent {email} created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
