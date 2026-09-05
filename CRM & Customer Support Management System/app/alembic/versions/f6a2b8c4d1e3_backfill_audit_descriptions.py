"""backfill missing audit descriptions

Revision ID: f6a2b8c4d1e3
Revises: e5f1a9b3c7d2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a2c8d4e9b1"
down_revision: Union[str, Sequence[str], None] = "e5f1a9b3c7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE audit_logs
        SET description = CASE
            WHEN action = 'ticket_status_changed'
                 AND previous_value->>'status' IS NOT NULL
                 AND new_value->>'status' IS NOT NULL
            THEN 'Ticket status changed from ' || (previous_value->>'status') || ' to ' || (new_value->>'status') || '.'
            ELSE INITCAP(REPLACE(action, '_', ' ')) || ' for ' || entity_type || ' ' || COALESCE(entity_id::text, 'unknown') || '.'
        END
        WHERE description IS NULL
    """))


def downgrade() -> None:
    pass
