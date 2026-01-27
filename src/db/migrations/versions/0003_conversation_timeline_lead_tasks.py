"""Add timeline, lead tasks, internal comments, audit logs, and roles

Revision ID: 0003_conversation_timeline_lead_tasks
Revises: 0002_onboarding_notifications
Create Date: 2024-07-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0003_conversation_timeline_lead_tasks"
down_revision = "0002_onboarding_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('agent', 'manager', 'admin')")
    op.add_column("users", sa.Column("role", sa.Enum("agent", "manager", "admin", name="user_role"), nullable=False, server_default="agent"))

    op.add_column("conversations", sa.Column("timeline", postgresql.JSONB(), nullable=True))

    op.create_table(
        "lead_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("priority", sa.Enum("low", "medium", "high", name="task_priority"), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum("todo", "doing", "done", name="task_status"), nullable=False, server_default="todo"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
    )

    op.create_table(
        "internal_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("internal_comments")
    op.drop_table("lead_tasks")
    op.drop_column("conversations", "timeline")
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS user_role")
