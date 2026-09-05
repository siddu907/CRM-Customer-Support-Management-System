# CRM Customer Support API
## Authentication

Protected endpoints require a bearer token in the `Authorization` header:

```text
Authorization: Bearer <access_token>
```

Obtain a token with `POST /auth/login`:

```json
{
  "email": "admin@gmail.com",
  "password": "ChangeMe123"
}
```

Swagger usage:

1. Call `/auth/login`.
2. Copy `access_token` from the response.
3. Click **Authorize**.
4. Paste the token into the bearer-token field.

Public registration always creates a customer account. Administrators and support agents are provisioned by scripts:

```powershell
python scripts/seed_admin.py admin@example.com "ChangeMe123" "System Admin"
python scripts/create_agent.py agent@example.com "AgentPass123" "Support Agent"
```

## Roles

| Role | Access summary |
|---|---|
| Customer | Own profile, own tickets, comments, attachments, notifications, and customer dashboard. |
| Support Agent | Assigned tickets, assigned-ticket comments/attachments, customer management, SLA views, and agent dashboard. |
| Admin | All customers, tickets, assignments, categories, SLA views, dashboards, notifications, and audit logs. |

Unauthorized requests return `401`. Authenticated users without permission return `403`.

## Authentication Endpoints

### `POST /auth/register`

Public customer self-registration. The role is always `customer`.

```json
{
  "full_name": "Jane Customer",
  "email": "jane@example.com",
  "password": "CustomerPass123",
  "phone_number": "+15550100",
  "company": "Acme",
  "address": "New York"
}
```

Returns `201` with the created user. Duplicate email returns `409`.

### `POST /auth/login`

Accepts JSON and returns a bearer token:

```json
{
  "email": "jane@example.com",
  "password": "CustomerPass123"
}
```

Wrong credentials return `401` with `{"detail": "Incorrect email or password"}`.

### `GET /auth/profile`

Returns the authenticated user profile.

### `PUT /auth/profile`

Updates the authenticated user's name and customer profile fields.

### `PUT /auth/change-password`

```json
{
  "current_password": "CustomerPass123",
  "new_password": "NewCustomerPass123"
}
```

Returns:

```json
{
  "message": "Password changed successfully"
}
```

## Customer Endpoints

### `POST /customers`

Admin or support-agent staff-assisted customer creation. It creates a login account and customer profile.

```json
{
  "full_name": "John Customer",
  "email": "john@example.com",
  "password": "CustomerPass123",
  "phone_number": "1234567890",
  "company": "ABC Company",
  "address": "New York",
  "status": "active"
}
```

Phone numbers may contain digits and common separators, but not letters.

### `GET /customers`

Admin/support-agent customer list. Query parameters:

```text
search, status, page, limit
```

### `GET /customers/{customer_id}`

Returns one customer. Customers may access only their own profile; staff may access customer records according to role.

### `PUT /customers/{customer_id}`

Updates customer data. Setting `status` to `inactive` also disables login while preserving support history.

### `DELETE /customers/{customer_id}`

Admin-only deactivation. It does not physically delete the customer or tickets.

```json
{
  "message": "Customer deleted successfully"
}
```

### `GET /customers/{customer_id}/tickets`

Returns tickets belonging to the customer. Supports `status`, `page`, and `limit`.

## Category Endpoints

### `POST /categories`

Admin-only category creation:

```json
{
  "name": "Billing",
  "description": "Billing and payment issues",
  "status": "active"
}
```

Duplicate names return `409`.

### `GET /categories`

Query parameters:

- Omit `active_only`: return both active and inactive categories.
- `active_only=true`: return active categories only.
- `active_only=false`: return inactive categories only.
- `search`: search category names.

### `GET /categories/{category_id}`

Returns one category.

### `PUT /categories/{category_id}`

Admin-only category update. Deactivate categories that should no longer be used.

### `DELETE /categories/{category_id}`

Admin-only physical deletion. Categories referenced by tickets cannot be deleted; deactivate them instead.

## Ticket Endpoints

### `POST /tickets`

Customers create tickets for themselves. Admins and support agents must provide an active `customer_id`.

```json
{
  "customer_id": 3,
  "category_id": 1,
  "subject": "Screen issue",
  "description": "Black screen",
  "priority": "critical"
}
```

Priorities:

```text
low, medium, high, critical
```

### `GET /tickets`

Returns tickets visible to the authenticated role.

Query parameters:

```text
page, limit, status, priority, category_id,
assigned_agent_id, search, sort_by, sort_order
```

Supported sorting:

```text
sort_by: created_at | updated_at | priority | status
sort_order: asc | desc
```

Customers see only their tickets. Support agents see only tickets assigned to them. Admins see all tickets.

### `GET /tickets/{ticket_id}`

Returns one ticket if the authenticated user has access.

### `PUT /tickets/{ticket_id}`

Updates permitted ticket fields:

```json
{
  "subject": "Updated subject",
  "description": "Updated description",
  "priority": "high",
  "status": "in_progress"
}
```

Customer permissions are limited to their own ticket details and cancellation. Agents manage assigned tickets. Admins manage all tickets.

### `PUT /tickets/{ticket_id}/assign`

Assigns an unassigned ticket to an active support agent:

```json
{
  "assigned_agent_id": 5
}
```

Assigning an already assigned ticket returns `422`; use `/reassign` instead. Assigning the same agent again returns `409`.

### `PUT /tickets/{ticket_id}/reassign`

Reassigns an already assigned ticket to another active support agent. It returns `422` if the ticket is currently unassigned.

### `PUT /tickets/{ticket_id}/resolve`

Moves an eligible ticket to `resolved`.

### `PUT /tickets/{ticket_id}/close`

Closes a resolved ticket. Closed tickets are immutable.

### `PUT /tickets/{ticket_id}/cancel`

Cancels an eligible ticket while preserving its record and history.

## Ticket Status Rules

Valid transitions are:

```text
open -> in_progress
open -> resolved
open -> cancelled
in_progress -> waiting_for_customer
in_progress -> resolved
in_progress -> cancelled
waiting_for_customer -> in_progress
waiting_for_customer -> cancelled
resolved -> closed
resolved -> open
```

Invalid examples include:

```text
closed -> in_progress
closed -> open
cancelled -> resolved
resolved -> in_progress
```

Invalid transitions return `422`. Closed and cancelled tickets cannot be modified.

## Comment Endpoints

### `POST /tickets/{ticket_id}/comments`

Adds a comment from an authorized customer or assigned agent:

```json
{
  "content": "We are investigating the issue."
}
```

The first support-agent comment records `first_response_at`.

### `GET /tickets/{ticket_id}/comments`

Lists comments for an accessible ticket.

### `PUT /comments/{comment_id}`

Updates an authorized comment. Customers cannot modify support-agent comments.

### `DELETE /comments/{comment_id}`

Deletes an authorized comment and returns:

```json
{
  "message": "Comment deleted successfully"
}
```

Closed and cancelled tickets do not accept comment changes.

## Attachment Endpoints

Allowed file types:

```text
PDF, JPG, JPEG, PNG, DOC, DOCX, TXT
```

Maximum size:

```text
10 MB
```

### `POST /tickets/{ticket_id}/attachments`

Multipart upload with form field `file`. Customers may upload to their own tickets; agents may upload to assigned tickets; admins may upload to any ticket.

### `GET /tickets/{ticket_id}/attachments`

Lists attachments for an accessible ticket.

### `GET /attachments/{attachment_id}`

Downloads an attachment if the user can access its ticket.

### `DELETE /attachments/{attachment_id}`

Deletes the attachment record and stored file:

```json
{
  "message": "Attachment deleted successfully"
}
```

## Notification Endpoints

### `GET /notifications`

Query parameters:

- Omit `unread_only`: return both read and unread notifications.
- `unread_only=true`: return unread notifications only.
- `unread_only=false`: return read notifications only.
- `page`, `limit`: pagination.

Notifications are private to the authenticated user.

### `PUT /notifications/{notification_id}/read`

Marks one owned notification as read.

### `PUT /notifications/read-all`

Marks all notifications belonging to the authenticated user as read.

## SLA Endpoints

### `GET /sla/tickets`

Lists SLA status for accessible tickets. Admins see all tickets; agents see assigned tickets.

### `GET /sla/breached`

Lists tickets whose response or resolution deadline has passed.

### `GET /sla/at-risk`

Lists tickets approaching an SLA deadline within the configured warning window.

Default SLA policies:

| Priority | Response | Resolution |
|---|---:|---:|
| Low | 48 hours | 48 hours |
| Medium | 24 hours | 24 hours |
| High | 8 hours | 8 hours |
| Critical | 2 hours | 2 hours |

Changing a ticket priority starts a fresh SLA window from the priority-change time.

## Dashboard Endpoints

Each dashboard is restricted to its matching role.

### `GET /dashboard/admin`

Returns:

```text
Total customers
Total support agents
Total tickets
Open tickets
In-progress tickets
Resolved tickets
Closed tickets
Critical tickets
SLA-breached tickets
Average resolution time (hours)
```

### `GET /dashboard/agent`

Returns assigned, open, pending, resolved, critical, and SLA-breached ticket metrics.

### `GET /dashboard/customer`

Returns total, open, in-progress, resolved, and closed ticket counts plus the 10 most recent tickets.

## Audit Log Endpoints

### `GET /audit-logs`

Admin-only paginated audit list. Supports `entity_type`, `user_id`, `page`, and `limit`.

### `GET /audit-logs/{log_id}`

Admin-only audit record lookup.

Important mutations create audit records with action, entity, previous value, new value, description, actor, and timestamp.

## Common Errors

| Status | Meaning |
|---:|---|
| 400 | Invalid business input or inactive customer/agent/category |
| 401 | Missing or invalid bearer token |
| 403 | Authenticated user lacks permission |
| 404 | Resource not found |
| 409 | Duplicate or conflicting operation |
| 422 | Validation failure or invalid state transition |
| 413 | Attachment exceeds the size limit |
| 500 | Unexpected server error; check application logs and database migration state |

## Database and Runtime Checks

```powershell
alembic upgrade head
pytest -q --basetemp .pytest-tmp
python -m compileall -q app alembic tests
```
