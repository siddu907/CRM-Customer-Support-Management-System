"""add missing customer company field

Revision ID: e5f1a9b3c7d2
Revises: d4e9f8a2b6c1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f1a9b3c7d2"
down_revision: Union[str, Sequence[str], None] = "d4e9f8a2b6c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "company" not in {column["name"] for column in inspector.get_columns("customers")}:
        op.add_column("customers", sa.Column("company", sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "company")