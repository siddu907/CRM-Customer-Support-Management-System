import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.enums import UserRole
from app.core.security import hash_password
from app.main import app
from app.models import Category, SLA, User
import app.services.notification as notification


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'crm_test.db'}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    db = Session()
    db.add(User(full_name="Platform Admin", email="admin@example.com", password_hash=hash_password("AdminPass123"), role=UserRole.ADMIN.value))
    db.add_all([
        Category(name="General", description="General support"),
        SLA(priority="low", response_time_hours=48, resolution_time_hours=48),
        SLA(priority="medium", response_time_hours=24, resolution_time_hours=24),
        SLA(priority="high", response_time_hours=8, resolution_time_hours=8),
        SLA(priority="critical", response_time_hours=2, resolution_time_hours=2),
    ])
    db.commit()
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    old_session_local = notification.SessionLocal
    notification.SessionLocal = Session
    app.dependency_overrides[get_db] = override_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    notification.SessionLocal = old_session_local
    Base.metadata.drop_all(engine)
    engine.dispose()


def auth_headers(client, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def provision_user(client, *, full_name: str, email: str, password: str, role: UserRole, is_active: bool = True) -> User:
    """Test-only controlled staff provisioning; there is no public users endpoint."""
    from app.core.database import get_db

    override = client.app.dependency_overrides[get_db]
    db = next(override())
    try:
        user = User(full_name=full_name, email=email, password_hash=hash_password(password), role=role.value, is_active=is_active)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture()
def admin_headers(client):
    return auth_headers(client, "admin@example.com", "AdminPass123")
