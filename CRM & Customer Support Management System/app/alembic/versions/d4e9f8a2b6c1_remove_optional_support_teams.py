"""remove optional support teams

Revision ID: d4e9f8a2b6c1
Revises: c2d8f7a1b4e6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e9f8a2b6c1"
down_revision: Union[str, Sequence[str], None] = "c2d8f7a1b4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" in inspector.get_table_names() and "team_id" in {column["name"] for column in inspector.get_columns("users")}: 
        op.drop_column("users", "team_id")
    if "teams" in inspector.get_table_names():
        op.drop_table("teams")


def downgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_users_team_id_teams", "teams", ["team_id"], ["id"], ondelete="SET NULL")