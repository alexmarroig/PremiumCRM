"""Add source event idempotency for automation events

Revision ID: 0005_automation_event_idempotency
Revises: 0004_automation_hub
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_automation_event_idempotency"
down_revision = "0004_automation_hub"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("automation_events", sa.Column("source_event_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_automation_event_source",
        "automation_events",
        ["user_id", "type", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_automation_event_source", "automation_events", type_="unique")
    op.drop_column("automation_events", "source_event_id")
