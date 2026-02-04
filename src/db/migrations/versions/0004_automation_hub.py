"""Add automation hub tables

Revision ID: 0004_automation_hub
Revises: 0003_conversation_timeline_lead_tasks
Create Date: 2024-07-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0004_automation_hub"
down_revision = "0003_conversation_timeline_lead_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE automation_delivery_status AS ENUM ('pending', 'sent', 'failed')")
    op.execute("CREATE TYPE automation_callback_status AS ENUM ('processed', 'rejected')")

    op.create_table(
        "automation_destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret_env_key", sa.String(), nullable=False),
        sa.Column("secret_masked", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("event_types", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "name", name="uq_automation_destination_name"),
    )

    op.create_table(
        "automation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_automation_events_user_type", "automation_events", ["user_id", "type"])

    op.create_table(
        "automation_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("pending", "sent", "failed", name="automation_delivery_status"), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["automation_destinations.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["automation_events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("event_id", "destination_id", name="uq_automation_delivery_event_destination"),
    )
    op.create_index("ix_automation_deliveries_status_retry", "automation_deliveries", ["status", "next_retry_at"])

    op.create_table(
        "automation_callback_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("processed", "rejected", name="automation_callback_status"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["automation_destinations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("event_id", "destination_id", name="uq_automation_callback_event_destination"),
    )


def downgrade() -> None:
    op.drop_table("automation_callback_events")
    op.drop_index("ix_automation_deliveries_status_retry", table_name="automation_deliveries")
    op.drop_table("automation_deliveries")
    op.drop_index("ix_automation_events_user_type", table_name="automation_events")
    op.drop_table("automation_events")
    op.drop_table("automation_destinations")
    op.execute("DROP TYPE IF EXISTS automation_callback_status")
    op.execute("DROP TYPE IF EXISTS automation_delivery_status")
