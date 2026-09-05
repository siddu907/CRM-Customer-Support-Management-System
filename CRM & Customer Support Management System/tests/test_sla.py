from datetime import timedelta

from tests.test_system_workflow import register_customer
from app.models.ticket import Ticket
from app.utils.helpers import utcnow


def test_sla_at_risk_and_breach_states(client, admin_headers):
	headers = register_customer(client, "sla-state@example.com")
	category = client.get("/categories", headers=headers).json()[0]
	ticket = client.post("/tickets", headers=headers, json={"category_id": category["id"], "subject": "SLA state", "description": "SLA state checks"}).json()
	from app.core.database import get_db
	db = next(client.app.dependency_overrides[get_db]())
	record = db.get(Ticket, ticket["id"])
	record.sla_response_deadline = utcnow() + timedelta(minutes=30)
	db.commit()
	db.close()
	assert client.get("/sla/at-risk", headers=admin_headers).json()["meta"]["total"] == 1
	db = next(client.app.dependency_overrides[get_db]())
	db.get(Ticket, ticket["id"]).sla_response_deadline = utcnow() - timedelta(minutes=1)
	db.commit()
	db.close()
	assert client.get("/sla/breached", headers=admin_headers).json()["meta"]["total"] == 1
