from tests.conftest import auth_headers
from tests.test_system_workflow import register_customer


def test_notifications_are_private_and_markable(client, admin_headers):
	headers = register_customer(client, "notification-owner@example.com")
	other_headers = register_customer(client, "notification-other@example.com")
	category = client.get("/categories", headers=headers).json()[0]
	client.post("/tickets", headers=headers, json={"category_id": category["id"], "subject": "Notification case", "description": "Creates a notification", "priority": "critical"})
	notifications = client.get("/notifications", headers=headers)
	assert notifications.status_code == 200
	assert notifications.json()["meta"]["total"] >= 1
	notification_id = notifications.json()["items"][0]["id"]
	assert client.put(f"/notifications/{notification_id}/read", headers=other_headers).status_code == 403
	marked = client.put(f"/notifications/{notification_id}/read", headers=headers)
	assert marked.status_code == 200
	assert marked.json()["is_read"] is True
	assert client.get("/notifications?unread_only=true", headers=headers).json()["meta"]["total"] == 0
	assert client.get("/notifications?unread_only=false", headers=headers).json()["meta"]["total"] == 1
	assert client.get("/notifications", headers=headers).json()["meta"]["total"] == 1
	assert client.put("/notifications/read-all", headers=headers).status_code == 200
