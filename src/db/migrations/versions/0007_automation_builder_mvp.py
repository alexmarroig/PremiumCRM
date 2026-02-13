"""Add automation builder MVP tables

Revision ID: 0007_automation_builder_mvp
Revises: 0006_automation_destination_secret_encrypted
Create Date: 2026-02-13 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_automation_builder_mvp"
down_revision = "0006_automation_destination_secret_encrypted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_event_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_tasks_user_source_event", "tasks", ["user_id", "source_event_id"]
    )

    op.create_table(
        "automation_builder_automations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("flow_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "automation_builder_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("automation_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("actions_executed", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["automation_id"], ["automation_builder_automations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_builder_runs_user_event",
        "automation_builder_runs",
        ["user_id", "event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_automation_builder_runs_user_event", table_name="automation_builder_runs")
    op.drop_table("automation_builder_runs")
    op.drop_table("automation_builder_automations")

    op.drop_constraint("uq_tasks_user_source_event", "tasks", type_="unique")
    op.drop_column("tasks", "source_event_id")
