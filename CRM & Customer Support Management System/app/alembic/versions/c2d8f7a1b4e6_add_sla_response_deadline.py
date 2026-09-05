"""add ticket response SLA deadline

Revision ID: c2d8f7a1b4e6
Revises: 6f0a5d2c9e1b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d8f7a1b4e6"
down_revision: Union[str, Sequence[str], None] = "6f0a5d2c9e1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    def add_column(table: str, column: sa.Column, fill: str | None = None, required: bool = False) -> None:
        if column.name in {item["name"] for item in inspector.get_columns(table)}:
            return
        op.add_column(table, column)
        if fill:
            op.execute(fill)
        if required:
            op.alter_column(table, column.name, nullable=False)

    add_column("categories", sa.Column("is_active", sa.Boolean(), nullable=True), "UPDATE categories SET is_active = TRUE", True)
    add_column("categories", sa.Column("created_at", sa.DateTime(), nullable=True), "UPDATE categories SET created_at = CURRENT_TIMESTAMP", True)
    add_column("categories", sa.Column("updated_at", sa.DateTime(), nullable=True), "UPDATE categories SET updated_at = CURRENT_TIMESTAMP", True)
    add_column("customers", sa.Column("status", sa.String(20), nullable=True), "UPDATE customers SET status = 'active'", True)
    add_column("customers", sa.Column("created_at", sa.DateTime(), nullable=True), "UPDATE customers SET created_at = CURRENT_TIMESTAMP", True)
    add_column("customers", sa.Column("updated_at", sa.DateTime(), nullable=True), "UPDATE customers SET updated_at = CURRENT_TIMESTAMP", True)
    add_column("tickets", sa.Column("ticket_number", sa.String(30), nullable=True), "UPDATE tickets SET ticket_number = 'TKT-' || LPAD(id::text, 6, '0')", True)
    if "ticket_number" in {item["name"] for item in inspector.get_columns("tickets")}:
        indexes = {item["name"] for item in inspector.get_indexes("tickets")}
        unique_constraints = {item["name"] for item in inspector.get_unique_constraints("tickets")}
        if "uq_tickets_ticket_number_compat" not in indexes and "uq_tickets_ticket_number_compat" not in unique_constraints:
            op.create_index("uq_tickets_ticket_number_compat", "tickets", ["ticket_number"], unique=True)
    add_column("tickets", sa.Column("sla_deadline", sa.DateTime(), nullable=True), "UPDATE tickets SET sla_deadline = created_at + INTERVAL '24 hours'", True)
    add_column("tickets", sa.Column("sla_response_deadline", sa.DateTime(), nullable=True), "UPDATE tickets SET sla_response_deadline = sla_deadline", True)
    add_column("tickets", sa.Column("first_response_at", sa.DateTime(), nullable=True))
    add_column("tickets", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    add_column("tickets", sa.Column("closed_at", sa.DateTime(), nullable=True))
    add_column("tickets", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    add_column("tickets", sa.Column("sla_status", sa.String(20), nullable=True), "UPDATE tickets SET sla_status = 'within_sla'", True)
    add_column("comments", sa.Column("updated_at", sa.DateTime(), nullable=True), "UPDATE comments SET updated_at = created_at", True)
    add_column("attachments", sa.Column("file_size", sa.Integer(), nullable=True), "UPDATE attachments SET file_size = 0", True)
    add_column("notifications", sa.Column("ticket_id", sa.Integer(), nullable=True))
    add_column("notifications", sa.Column("event_type", sa.String(50), nullable=True), "UPDATE notifications SET event_type = 'legacy'", True)
    add_column("audit_logs", sa.Column("previous_value", sa.JSON(), nullable=True))
    add_column("audit_logs", sa.Column("new_value", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "sla_response_deadline")