from tests.test_system_workflow import register_customer


def test_audit_logs_are_admin_only_and_filterable(client, admin_headers):
	customer_headers = register_customer(client, "audit-customer@example.com")
	assert client.get("/audit-logs", headers=customer_headers).status_code == 403
	logs = client.get("/audit-logs?entity_type=user&page=1&limit=10", headers=admin_headers)
	assert logs.status_code == 200
	assert logs.json()["meta"]["total"] >= 1
	assert all(item["entity_type"] == "user" for item in logs.json()["items"])
	assert client.get("/audit-logs/999999", headers=admin_headers).status_code == 404
