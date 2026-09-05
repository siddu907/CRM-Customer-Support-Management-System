from datetime import timedelta

from app.models.ticket import Ticket
from app.utils.helpers import utcnow
from app.core.enums import UserRole
from tests.conftest import auth_headers, provision_user


def register_customer(client, email="customer@example.com"):
    response = client.post("/auth/register", json={
        "full_name": "Customer One", "email": email, "password": "CustomerPass123",
        "phone_number": "1234567890", "company": "Acme",
    })
    assert response.status_code == 201, response.text
    return auth_headers(client, email, "CustomerPass123")


def test_ticket_lifecycle_permissions_notifications_and_audit(client, admin_headers):
    customer_headers = register_customer(client)
    duplicate = client.post("/auth/register", json={"full_name": "Again", "email": "customer@example.com", "password": "CustomerPass123"})
    assert duplicate.status_code == 409

    category = client.get("/categories", headers=customer_headers).json()[0]
    created = client.post("/tickets", headers=customer_headers, json={
        "category_id": category["id"], "subject": "Payment is unavailable", "description": "Card payment fails at checkout.", "priority": "critical",
    })
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["ticket_number"].startswith("TKT-")
    assert ticket["priority"] == "critical"

    # Inactive agents are deliberately rejected by the assignment service.
    agent = provision_user(client, full_name="Agent One", email="agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
    assigned = client.put(f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id})
    assert assigned.status_code == 200, assigned.text
    agent_headers = auth_headers(client, "agent@example.com", "AgentPass123")

    assert client.put(f"/tickets/{ticket['id']}", headers=customer_headers, json={"status": "in_progress"}).status_code == 403
    assert client.put(f"/tickets/{ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 200
    comment = client.post(f"/tickets/{ticket['id']}/comments", headers=agent_headers, json={"content": "We are checking the payment gateway."})
    assert comment.status_code == 201, comment.text
    assert client.put(f"/tickets/{ticket['id']}/resolve", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{ticket['id']}/close", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 409
    assert client.post(f"/tickets/{ticket['id']}/comments", headers=customer_headers, json={"content": "Please reopen it"}).status_code == 409

    notifications = client.get("/notifications", headers=customer_headers)
    assert notifications.status_code == 200
    assert notifications.json()["meta"]["total"] >= 2
    audit_logs = client.get("/audit-logs", headers=admin_headers)
    assert audit_logs.status_code == 200
    status_log = next(log for log in audit_logs.json()["items"] if log["action"] == "ticket_status_changed")
    assert status_log["description"] == "Ticket status changed from resolved to closed."


def test_categories_filters_attachments_and_sla(client, admin_headers):
    customer_headers = register_customer(client, "file-customer@example.com")
    duplicate_category = client.post("/categories", headers=admin_headers, json={"name": "General"})
    assert duplicate_category.status_code == 409
    category = client.get("/categories", headers=customer_headers).json()[0]
    ticket_response = client.post("/tickets", headers=customer_headers, json={
        "category_id": category["id"], "subject": "Upload evidence", "description": "Please see attached error output.", "priority": "high",
    })
    ticket_id = ticket_response.json()["id"]
    upload = client.post(f"/tickets/{ticket_id}/attachments", headers=customer_headers, files={"file": ("error.txt", b"error details", "text/plain")})
    assert upload.status_code == 201, upload.text
    assert upload.json()["file_size"] == len(b"error details")
    assert client.get(f"/attachments/{upload.json()['id']}", headers=customer_headers).status_code == 200

    # Move deadline into the past through the test database then confirm monitoring output.
    from app.core.database import get_db
    override = client.app.dependency_overrides[get_db]
    db = next(override())
    ticket = db.get(Ticket, ticket_id)
    ticket.sla_deadline = utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()
    breached = client.get("/sla/breached", headers=admin_headers)
    assert breached.status_code == 200
    assert breached.json()["meta"]["total"] == 1
    dashboard = client.get("/dashboard/customer", headers=customer_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["total_tickets"] == 1


def test_inactive_agent_assignment_rule(client, admin_headers):
    agent = provision_user(client, full_name="Inactive Agent", email="inactive-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT, is_active=False)

    customer_headers = register_customer(client, "inactive-rule@example.com")
    category = client.get("/categories", headers=customer_headers).json()[0]
    ticket = client.post("/tickets", headers=customer_headers, json={
        "category_id": category["id"], "subject": "Billing needs help", "description": "Need an invoice adjustment.",
    }).json()
    rejected = client.put(f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id})
    assert rejected.status_code == 400
    assert "Inactive support agents" in rejected.json()["detail"]


def test_admin_customer_history(client, admin_headers):
    customer_headers = register_customer(client, "history@example.com")
    category = client.get("/categories", headers=customer_headers).json()[0]
    ticket = client.post("/tickets", headers=customer_headers, json={
        "category_id": category["id"], "subject": "Keep my history", "description": "This must remain available.",
    }).json()
    customer = client.get("/auth/profile", headers=customer_headers).json()
    customer_record = next(item for item in client.get("/customers", headers=admin_headers).json()["items"] if item["email"] == customer["email"])
    customer_id = customer_record["id"]
    customer_detail = client.get(f"/customers/{customer_id}", headers=admin_headers)
    assert customer_detail.status_code == 200
    deleted = client.delete(f"/customers/{customer_id}", headers=admin_headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Customer deleted successfully"}
    assert client.get(f"/tickets/{ticket['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"/customers/{customer_id}", headers=admin_headers).json()["status"] == "inactive"


def test_agent_sla_scope_and_response_breach(client, admin_headers):
    agent = provision_user(client, full_name="SLA Agent", email="sla-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
    first_customer_headers = register_customer(client, "sla-one@example.com")
    second_customer_headers = register_customer(client, "sla-two@example.com")
    category = client.get("/categories", headers=first_customer_headers).json()[0]
    first_ticket = client.post("/tickets", headers=first_customer_headers, json={
        "category_id": category["id"], "subject": "Assigned SLA ticket", "description": "Assigned to the agent.",
    }).json()
    second_ticket = client.post("/tickets", headers=second_customer_headers, json={
        "category_id": category["id"], "subject": "Private SLA ticket", "description": "Must stay out of the agent queue.",
    }).json()
    assert client.put(f"/tickets/{first_ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200

    from app.core.database import get_db
    from app.utils.helpers import utcnow
    override = client.app.dependency_overrides[get_db]
    db = next(override())
    db.get(Ticket, first_ticket["id"]).sla_response_deadline = utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()

    agent_headers = auth_headers(client, "sla-agent@example.com", "AgentPass123")
    visible = client.get("/sla/tickets", headers=agent_headers)
    assert visible.status_code == 200
    assert [item["id"] for item in visible.json()["items"]] == [first_ticket["id"]]
    breached = client.get("/sla/breached", headers=agent_headers)
    assert breached.status_code == 200
    assert [item["id"] for item in breached.json()["items"]] == [first_ticket["id"]]
    assert second_ticket["id"] not in [item["id"] for item in visible.json()["items"]]


def test_assignment_invalid_status_transitions_are_rejected(client, admin_headers):
    customer_headers = register_customer(client, "transition-rules@example.com")
    category = client.get("/categories", headers=customer_headers).json()[0]
    agent = provision_user(client, full_name="Transition Agent", email="transition-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
    agent_headers = auth_headers(client, "transition-agent@example.com", "AgentPass123")

    def create_ticket(subject: str):
        return client.post(f"/tickets", headers=customer_headers, json={
            "category_id": category["id"], "subject": subject, "description": "Transition validation",
        }).json()

    closed_ticket = create_ticket("Closed rules")
    assert client.put(f"/tickets/{closed_ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200
    assert client.put(f"/tickets/{closed_ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 200
    assert client.put(f"/tickets/{closed_ticket['id']}/resolve", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{closed_ticket['id']}/close", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{closed_ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 409
    assert client.put(f"/tickets/{closed_ticket['id']}", headers=agent_headers, json={"status": "open"}).status_code == 409

    cancelled_ticket = create_ticket("Cancelled rules")
    assert client.put(f"/tickets/{cancelled_ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200
    assert client.put(f"/tickets/{cancelled_ticket['id']}/cancel", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{cancelled_ticket['id']}/resolve", headers=agent_headers).status_code == 422

    reopened_ticket = create_ticket("Resolved reopen rules")
    assert client.put(f"/tickets/{reopened_ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200
    assert client.put(f"/tickets/{reopened_ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 200
    assert client.put(f"/tickets/{reopened_ticket['id']}/resolve", headers=agent_headers).status_code == 200
    assert client.put(f"/tickets/{reopened_ticket['id']}", headers=agent_headers, json={"status": "in_progress"}).status_code == 422


def test_open_ticket_can_be_resolved_directly(client, admin_headers):
    customer_headers = register_customer(client, "direct-resolve@example.com")
    category = client.get("/categories", headers=customer_headers).json()[0]
    ticket = client.post("/tickets", headers=customer_headers, json={
        "category_id": category["id"], "subject": "Direct resolution", "description": "Resolve from open",
    }).json()
    agent = provision_user(client, full_name="Direct Resolve Agent", email="direct-resolve-agent@example.com", password="AgentPass123", role=UserRole.SUPPORT_AGENT)
    agent_headers = auth_headers(client, "direct-resolve-agent@example.com", "AgentPass123")
    assert client.put(f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assigned_agent_id": agent.id}).status_code == 200
    resolved = client.put(f"/tickets/{ticket['id']}/resolve", headers=agent_headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
