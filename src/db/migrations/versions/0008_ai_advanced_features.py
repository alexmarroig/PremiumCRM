"""ai advanced features

Revision ID: 0008
Revises: 0007
Create Date: 2024-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('context_summary', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('personality_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('conversations', sa.Column('simulation_enabled', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('conversations', 'simulation_enabled')
    op.drop_column('conversations', 'personality_analysis')
    op.drop_column('conversations', 'context_summary')
