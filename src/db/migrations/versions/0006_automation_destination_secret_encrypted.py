"""Add encrypted secret storage for automation destinations

Revision ID: 0006_automation_destination_secret_encrypted
Revises: 0005_automation_event_idempotency
Create Date: 2026-02-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_automation_destination_secret_encrypted"
down_revision = "0005_automation_event_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("automation_destinations", sa.Column("secret_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("automation_destinations", "secret_encrypted")
