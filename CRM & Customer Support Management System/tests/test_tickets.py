from tests.conftest import auth_headers, provision_user
from tests.test_system_workflow import register_customer
from app.core.enums import UserRole
from app.models.ticket import Ticket
from app.utils.helpers import as_utc, utcnow


def test_ticket_scope_filters_and_inactive_customer_rule(client, admin_headers):
	customer_headers = register_customer(client, "ticket-owner@example.com")
	other_headers = register_customer(client, "other-owner@example.com")
	category = client.get("/categories", headers=customer_headers).json()[0]
	created = client.post("/tickets", headers=customer_headers, json={"category_id": category["id"], "subject": "Payment search case", "description": "Payment search description", "priority": "high"})
	assert created.status_code == 201
	ticket_id = created.json()["id"]
	assert client.get(f"/tickets/{ticket_id}", headers=other_headers).status_code == 403
	assert client.get("/tickets?search=Payment", headers=customer_headers).json()["meta"]["total"] == 1
	assert client.put(f"/tickets/{ticket_id}", headers=customer_headers, json={"priority": "critical"}).status_code == 403

	customer = next(item for item in client.get("/customers", headers=admin_headers).json()["items"] if item["email"] == "ticket-owner@example.com")
	assert client.put(f"/customers/{customer['id']}", headers=admin_headers, json={"status": "inactive"}).status_code == 200
	assert client.post("/tickets", headers=admin_headers, json={"customer_id": customer["id"], "category_id": category["id"], "subject": "Blocked ticket", "description": "Inactive customer"}).status_code == 400


def test_agent_cannot_manage_another_agents_ticket(client, admin_headers):
	customer_headers = register_customer(client, "assigned-owner@example.com")
	category = client.get("/categories", headers=customer_headers).json()[0]
	ticket = client.post("/tickets", headers=customer_headers, json={"category_id": category["id"], "subject": "Assigned ticket", "description": "Assignment check"}).json()
	first = provision_user(client, full_name="First Agent", email="first-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
	second = provision_user(client, full_name="Second Agent", email="second-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
	assert client.put(f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": first.id}).status_code == 200
	second_headers = auth_headers(client, "second-agent@example.com", "AgentPass123")
	assert client.get(f"/tickets/{ticket['id']}", headers=second_headers).status_code == 403
	assert client.put(f"/tickets/{ticket['id']}/assign", headers=second_headers, json={"assigned_agent_id": second.id}).status_code == 403


def test_priority_change_starts_new_sla_window(client, admin_headers):
	customer_headers = register_customer(client, "priority-sla@example.com")
	category = client.get("/categories", headers=customer_headers).json()[0]
	ticket = client.post(f"/tickets", headers=customer_headers, json={
		"category_id": category["id"], "subject": "Priority SLA", "description": "Priority update resets SLA", "priority": "medium",
	}).json()

	updated = client.put(f"/tickets/{ticket['id']}", headers=admin_headers, json={"priority": "critical"})
	assert updated.status_code == 200

	from app.core.database import get_db
	db = next(client.app.dependency_overrides[get_db]())
	record = db.get(Ticket, ticket["id"])
	now = utcnow()
	assert 1.9 <= (as_utc(record.sla_deadline) - now).total_seconds() / 3600 <= 2.1
	db.close()


def test_assign_endpoint_rejects_duplicates_and_reassigns(client, admin_headers):
	customer_headers = register_customer(client, "reassign-owner@example.com")
	category = client.get("/categories", headers=customer_headers).json()[0]
	ticket = client.post("/tickets", headers=customer_headers, json={
		"category_id": category["id"], "subject": "Reassignment case", "description": "Assignment behavior",
	}).json()
	first = provision_user(client, full_name="First Assignment Agent", email="first-assignment@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
	second = provision_user(client, full_name="Second Assignment Agent", email="second-assignment@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)

	assign_url = f"/tickets/{ticket['id']}/assign"
	assert client.put(assign_url, headers=admin_headers, json={"assigned_agent_id": first.id}).status_code == 200
	duplicate = client.put(assign_url, headers=admin_headers, json={"assigned_agent_id": first.id})
	assert duplicate.status_code == 409
	assert "already assigned" in duplicate.json()["detail"]

	not_reassigned = client.put(assign_url, headers=admin_headers, json={"assigned_agent_id": second.id})
	assert not_reassigned.status_code == 422
	assert "reassign endpoint" in not_reassigned.json()["detail"]

	reassigned = client.put(f"/tickets/{ticket['id']}/reassign", headers=admin_headers, json={"assigned_agent_id": second.id})
	assert reassigned.status_code == 200
	assert reassigned.json()["assigned_agent_id"] == second.id
