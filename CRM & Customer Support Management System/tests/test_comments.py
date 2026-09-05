from tests.conftest import auth_headers, provision_user
from tests.test_system_workflow import register_customer
from app.core.enums import UserRole


def test_comment_authorization_and_first_response(client, admin_headers):
	customer_headers = register_customer(client, "comment-owner@example.com")
	category = client.get("/categories", headers=customer_headers).json()[0]
	ticket = client.post("/tickets", headers=customer_headers, json={"category_id": category["id"], "subject": "Comment case", "description": "Comment authorization"}).json()
	agent = provision_user(client, full_name="Comment Agent", email="comment-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
	assert client.put(f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200
	agent_headers = auth_headers(client, "comment-agent@example.com", "AgentPass123")
	comment = client.post(f"/tickets/{ticket['id']}/comments", headers=agent_headers, json={"content": "Investigating now"})
	assert comment.status_code == 201
	assert client.get(f"/tickets/{ticket['id']}", headers=customer_headers).json()["first_response_at"] is not None
	assert client.put(f"/comments/{comment.json()['id']}", headers=customer_headers, json={"content": "Tamper"}).status_code == 403
	assert client.post(f"/tickets/{ticket['id']}/comments", headers=customer_headers, json={"content": "Customer reply"}).status_code == 201
