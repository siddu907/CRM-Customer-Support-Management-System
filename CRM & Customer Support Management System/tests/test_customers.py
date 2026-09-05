from tests.conftest import auth_headers


def test_customer_isolation_and_status_disables_login(client, admin_headers):
	first = client.post("/auth/register", json={"full_name": "First Customer", "email": "first@example.com", "password": "CustomerPass123"})
	assert first.status_code == 201
	client.post("/auth/register", json={"full_name": "Second Customer", "email": "second@example.com", "password": "CustomerPass123"})
	first_headers = auth_headers(client, "first@example.com", "CustomerPass123")
	second_headers = auth_headers(client, "second@example.com", "CustomerPass123")
	customers = client.get("/customers", headers=first_headers)
	assert customers.status_code == 403
	profile = client.get("/auth/profile", headers=first_headers).json()
	first_id = next(item["id"] for item in client.get("/customers", headers=admin_headers).json()["items"] if item["email"] == profile["email"])
	assert client.get(f"/customers/{first_id}", headers=second_headers).status_code == 403
	assert client.put(f"/customers/{first_id}", headers=admin_headers, json={"status": "inactive"}).status_code == 200
	assert client.post("/auth/login", json={"email": "first@example.com", "password": "CustomerPass123"}).status_code == 403
	assert client.put(f"/customers/{first_id}", headers=admin_headers, json={"status": "active"}).status_code == 200
	assert client.post("/auth/login", json={"email": "first@example.com", "password": "CustomerPass123"}).status_code == 200


def test_customer_phone_rejects_letters(client):
	response = client.post("/auth/register", json={"full_name": "Phone Customer", "email": "phone-check@example.com", "password": "CustomerPass123", "phone_number": "555ABC1234"})
	assert response.status_code == 422
