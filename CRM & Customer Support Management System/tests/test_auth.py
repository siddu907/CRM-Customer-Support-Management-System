from tests.conftest import auth_headers, provision_user
from app.core.enums import UserRole


def test_registration_normalizes_email_and_rejects_invalid_input(client):
	response = client.post("/auth/register", json={
		"full_name": "Normalized Customer", "email": "  USER@Example.COM ", "password": "CustomerPass123",
	})
	assert response.status_code == 201
	assert response.json()["role"] == "customer"
	assert client.post("/auth/register", json={"full_name": "X", "email": "bad", "password": "short"}).status_code == 422
	assert client.post("/auth/register", json={"full_name": "Another", "email": "user@example.com", "password": "CustomerPass123"}).status_code == 409
	assert client.post("/auth/register", json={"full_name": "Phone Customer", "email": "phone@example.com", "password": "CustomerPass123", "phone_number": "12AB456"}).status_code == 422


def test_authentication_profile_and_password_change(client):
	client.post("/auth/register", json={"full_name": "Password Customer", "email": "password@example.com", "password": "CustomerPass123"})
	headers = auth_headers(client, "password@example.com", "CustomerPass123")
	assert client.get("/auth/profile", headers=headers).status_code == 200
	assert client.put("/auth/profile", headers=headers, json={"full_name": "Updated Customer"}).status_code == 200
	changed = client.put("/auth/change-password", headers=headers, json={"current_password": "CustomerPass123", "new_password": "NewCustomer123"})
	assert changed.status_code == 200
	assert changed.json() == {"message": "Password changed successfully"}
	assert client.post("/auth/login", json={"email": "password@example.com", "password": "CustomerPass123"}).status_code == 401
	assert client.post("/auth/login", json={"email": "password@example.com", "password": "NewCustomer123"}).status_code == 200


def test_json_login_works_for_swagger(client):
	client.post("/auth/register", json={"full_name": "Swagger Customer", "email": "swagger@example.com", "password": "CustomerPass123"})
	response = client.post("/auth/login", json={"email": "swagger@example.com", "password": "CustomerPass123"})
	assert response.status_code == 200, response.text
	assert response.json()["token_type"] == "bearer"


def test_inactive_and_invalid_tokens_are_rejected(client):
	provision_user(client, full_name="Inactive", email="inactive@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT, is_active=False)
	assert client.post("/auth/login", json={"email": "inactive@example.com", "password": "AgentPass123"}).status_code == 403
	assert client.get("/auth/profile").status_code == 401
	assert client.get("/auth/profile", headers={"Authorization": "Bearer malformed"}).status_code == 401
