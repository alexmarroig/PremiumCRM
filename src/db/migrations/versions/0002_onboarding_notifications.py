"""Add onboarding notification type and message column

Revision ID: 0002_onboarding_notifications
Revises: 0001_init
Create Date: 2024-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_onboarding_notifications"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'onboarding'")
    op.execute("ALTER TYPE notification_entity ADD VALUE IF NOT EXISTS 'system'")
    op.add_column("notifications", sa.Column("message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "message")
    # Enum values cannot be removed safely in PostgreSQL; keeping added values in downgrade.
