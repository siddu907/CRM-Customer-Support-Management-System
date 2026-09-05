# CRM & Customer Support Management System

A FastAPI backend for customer support, covering secure role-based access, customer records, ticket workflows, comments, attachments, notifications, SLA monitoring, dashboards, and audit history.

## Stack

- FastAPI + Pydantic v2 with OpenAPI/Swagger at `/docs`
- SQLAlchemy 2 ORM + PostgreSQL + Alembic
- JWT bearer authentication and PBKDF2-SHA256 password hashing
- Repository and service layers with explicit transaction boundaries
- FastAPI `BackgroundTasks` for notification persistence and scheduled SLA monitoring

## Setup

1. Create PostgreSQL database `crm_db`.
2. Copy `.env.example` to `.env` and set a strong `SECRET_KEY` and `DATABASE_URL`.
3. Install dependencies: `python -m pip install -r requirements.txt`.
4. Apply the schema: `alembic upgrade head`.
5. Create the initial administrator: `python scripts/seed_admin.py admin@example.com "ChangeMe123" "System Admin"`.
6. Create a support agent: `python scripts/create_agent.py agent@example.com "AgentPass123" "Support Agent"`.
7. Run the API: `uvicorn app.main:app --reload`.
8. Open `http://127.0.0.1:8000/docs` and use the bearer token returned by `/auth/login` in the **Authorize** dialog.

## Roles and authorization

| Role | Permissions |
|---|---|
| Customer | Registers itself, manages its own profile and tickets, comments and attachments; cannot access other customers’ data. |
| Support agent | Works only on assigned tickets, can claim an unassigned ticket, views assigned-ticket SLA status and the agent dashboard, and manages customers. |
| Admin | Manages all customers, categories, tickets, dashboards, and audit logs. |

Public registration always creates a `customer` account, preventing privilege escalation. The initial administrator is created with `scripts/seed_admin.py`; support-agent records are created with `scripts/create_agent.py`.

## Key API groups

| Group | Main routes |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/profile`, `PUT /auth/profile`, `PUT /auth/change-password` |
| Customers | `POST/GET /customers`, `GET/PUT/DELETE /customers/{id}`, `GET /customers/{id}/tickets` |
| Categories | `POST/GET /categories`, `GET/PUT/DELETE /categories/{id}` |
| Tickets | `POST /tickets`, `GET /tickets`, `GET/PUT /tickets/{id}`, assignment through `/tickets/{id}/assign`, reassignment through `/tickets/{id}/reassign`, resolve, close, and cancel |
| Comments | `POST/GET /tickets/{ticket_id}/comments`, `PUT/DELETE /comments/{id}` |
| Attachments | `POST/GET /tickets/{ticket_id}/attachments`, `GET/DELETE /attachments/{id}` |
| Notifications | `GET /notifications`, `PUT /notifications/{id}/read`, `PUT /notifications/read-all` |
| SLA | `GET /sla/tickets`, `GET /sla/breached`, `GET /sla/at-risk` |
| Dashboards | `GET /dashboard/admin`, `GET /dashboard/agent`, `GET /dashboard/customer` |
| Audit logs | `GET /audit-logs`, `GET /audit-logs/{id}` |

List endpoints use pagination where supported. Ticket lists support `page`, `limit`, `search`, `status`, `priority`, `category_id`, `assigned_agent_id`, `sort_by`, and `sort_order`. Customer, customer-ticket, notification, SLA, and audit-log lists also support pagination. A complete ready-to-import collection is at [postman/CRM-Customer-Support.postman_collection.json](postman/CRM-Customer-Support.postman_collection.json).

`GET /categories` supports three states: omit `active_only` for both active and inactive categories, use `active_only=true` for active categories, or use `active_only=false` for inactive categories. `GET /notifications` similarly returns both when `unread_only` is omitted, unread notifications when it is `true`, and read notifications when it is `false`.

## Ticket and SLA rules

Priorities are `low`, `medium`, `high`, and `critical`. Default response/resolution policies are 48, 24, 8, and 2 hours respectively. Every ticket stores response and resolution SLA deadlines, first staff response, resolution time, and computed `within_sla`, `at_risk`, or `breached` state. When a ticket priority changes, a fresh SLA window starts at the time of that change.

Valid transitions are:

```text
open → in_progress → waiting_for_customer → in_progress → resolved → closed
open/in_progress/waiting_for_customer → cancelled
resolved → open  (explicit reopen)
```

Closed and cancelled tickets are immutable. Inactive agents cannot receive assignments. Use `/tickets/{id}/assign` only for unassigned tickets and `/tickets/{id}/reassign` only for already assigned tickets. Repeating an assignment to the same agent returns a conflict. Comments and attachments are refused for terminal tickets. Supported attachment extensions are PDF, JPG/JPEG, PNG, DOC/DOCX, and TXT, with a 10 MB default limit.

Customer deletion deactivates the account and preserves support history. Category deletion is blocked when tickets reference the category. Comment and attachment deletion return JSON confirmation messages. Ticket cancellation preserves the ticket as a cancelled record.

## Background work and production scaling

Ticket creation, assignment/reassignment, status changes, comments, resolution/closure, and critical tickets queue recipient notifications after the transactional request path. The PostgreSQL application lifecycle runs SLA checks every `BACKGROUND_JOB_INTERVAL_SECONDS` seconds and creates daily support reports. `BackgroundTasks` is appropriate for the requested basic system. For durable high-volume production work, point the same service events at a Celery/RQ worker and broker, use object storage for attachments, and deploy multiple stateless API workers behind a load balancer.

## Verification

Run `pytest -q --basetemp .pytest-tmp`. The automated API and functional tests validate JWT login, RBAC, customer isolation, duplicate constraints, assignment/reassignment, lifecycle transition checks, comments, attachments, background notifications, SLA breaches, dashboards, category and notification filters, phone validation, audit descriptions, and database workflows.


