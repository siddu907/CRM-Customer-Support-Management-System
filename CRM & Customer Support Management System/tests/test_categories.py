from tests.test_system_workflow import register_customer


def test_category_admin_rules_and_search(client, admin_headers):
	customer_headers = register_customer(client, "category-customer@example.com")
	assert client.post("/categories", headers=customer_headers, json={"name": "Customer Category"}).status_code == 403
	created = client.post("/categories", headers=admin_headers, json={"name": "  Billing  "})
	assert created.status_code == 201
	assert client.post("/categories", headers=admin_headers, json={"name": "billing"}).status_code == 409
	assert client.get("/categories?search=bill", headers=customer_headers).json()[0]["name"] == "Billing"
	assert client.put(f"/categories/{created.json()['id']}", headers=admin_headers, json={"status": "inactive"}).status_code == 200
	assert client.get("/categories?active_only=false", headers=customer_headers).json()[0]["name"] == "Billing"
	assert client.get("/categories?active_only=true&search=bill", headers=customer_headers).json() == []
	assert {item["name"] for item in client.get("/categories?search=bill", headers=customer_headers).json()} == {"Billing"}
	assert {item["name"] for item in client.get("/categories", headers=customer_headers).json()} == {"General", "Billing"}
