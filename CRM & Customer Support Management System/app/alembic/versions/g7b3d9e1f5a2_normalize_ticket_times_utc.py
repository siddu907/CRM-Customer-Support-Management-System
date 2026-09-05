"""normalize legacy ticket timestamps to UTC

Revision ID: g7b3d9e1f5a2
Revises: f6a2c8d4e9b1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g7b3d9e1f5a2"
down_revision: Union[str, Sequence[str], None] = "f6a2c8d4e9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TIMESTAMP_COLUMNS = (
    "created_at",
    "updated_at",
    "sla_response_deadline",
    "sla_deadline",
    "first_response_at",
    "resolved_at",
    "closed_at",
    "cancelled_at",
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("tickets")}
    for column in _TIMESTAMP_COLUMNS:
        if column in columns:
            op.execute(sa.text(f"UPDATE tickets SET {column} = {column} - INTERVAL '5 hours 30 minutes' WHERE {column} IS NOT NULL"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("tickets")}
    for column in _TIMESTAMP_COLUMNS:
        if column in columns:
            op.execute(sa.text(f"UPDATE tickets SET {column} = {column} + INTERVAL '5 hours 30 minutes' WHERE {column} IS NOT NULL"))
