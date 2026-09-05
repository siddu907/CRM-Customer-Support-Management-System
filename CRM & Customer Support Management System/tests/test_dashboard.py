from tests.test_system_workflow import register_customer


def test_dashboards_are_role_specific(client, admin_headers):
	customer_headers = register_customer(client, "dashboard-customer@example.com")
	assert client.get("/dashboard/admin", headers=customer_headers).status_code == 403
	assert client.get("/dashboard/customer", headers=admin_headers).status_code == 403
	category = client.get("/categories", headers=customer_headers).json()[0]
	client.post("/tickets", headers=customer_headers, json={"category_id": category["id"], "subject": "Dashboard ticket", "description": "Dashboard metrics"})
	dashboard = client.get("/dashboard/customer", headers=customer_headers)
	assert dashboard.status_code == 200
	assert dashboard.json()["metrics"]["total_tickets"] == 1
	assert set(dashboard.json()["metrics"]) == {"total_tickets", "open_tickets", "in_progress_tickets", "resolved_tickets", "closed_tickets"}
