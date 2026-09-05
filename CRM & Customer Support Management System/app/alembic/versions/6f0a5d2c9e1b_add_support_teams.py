"""add support teams and agent membership

Revision ID: 6f0a5d2c9e1b
Revises: eba9e61bc54e
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "6f0a5d2c9e1b"
down_revision = "eba9e61bc54e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_teams_name", "teams", ["name"])
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_users_team_id", ["team_id"])
        batch_op.create_foreign_key("fk_users_team_id_teams", "teams", ["team_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_team_id_teams", type_="foreignkey")
        batch_op.drop_index("ix_users_team_id")
        batch_op.drop_column("team_id")
    op.drop_table("teams")
