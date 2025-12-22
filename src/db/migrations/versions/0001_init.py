"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    channel_enum = sa.Enum('whatsapp', 'instagram', 'messenger', 'email', 'other', name='channel_type')
    conversation_status_enum = sa.Enum('open', 'closed', name='conversation_status')
    direction_enum = sa.Enum('inbound', 'outbound', name='message_direction')
    task_status_enum = sa.Enum('todo', 'doing', 'done', name='task_status')
    task_priority_enum = sa.Enum('low', 'medium', 'high', name='task_priority')
    notification_type_enum = sa.Enum('urgent_message', 'overdue_task', 'stalled_lead', 'rule_match', name='notification_type')
    notification_entity_enum = sa.Enum('conversation', 'task', 'rule', name='notification_entity')

    op.create_table(
        'users',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
    )

    op.create_table(
        'channels',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', channel_enum, nullable=False),
        sa.Column('external_id', sa.String()),
    )

    op.create_table(
        'contacts',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('handle', sa.String(), nullable=False),
        sa.Column('avatar_url', sa.String()),
        sa.Column('tags', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.UniqueConstraint('user_id', 'handle', name='uq_contact_handle'),
    )
    op.create_index('ix_contacts_user_handle', 'contacts', ['user_id', 'handle'])

    op.create_table(
        'contact_settings',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('contact_id', sa.UUID(), sa.ForeignKey('contacts.id'), primary_key=True),
        sa.Column('negotiation_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('base_price_default', sa.Numeric()),
        sa.Column('custom_price', sa.Numeric()),
        sa.Column('vip', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('preferred_tone', sa.String()),
    )

    op.create_table(
        'conversations',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('contact_id', sa.UUID(), sa.ForeignKey('contacts.id'), nullable=False),
        sa.Column('channel_id', sa.UUID(), sa.ForeignKey('channels.id'), nullable=False),
        sa.Column('status', conversation_status_enum, server_default='open', nullable=False),
        sa.Column('last_message_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('unread_count', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_index('ix_conversations_user_last', 'conversations', ['user_id', 'last_message_at'])

    op.create_table(
        'messages',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('conversation_id', sa.UUID(), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('direction', direction_enum, nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.Column('channel_message_id', sa.String()),
        sa.Column('ai_classification', sa.JSON()),
    )
    op.create_index('ix_messages_conversation', 'messages', ['conversation_id', 'created_at'])

    op.create_table(
        'tasks',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), sa.ForeignKey('conversations.id')),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('due_date', sa.Date()),
        sa.Column('status', task_status_enum, server_default='todo', nullable=False),
        sa.Column('priority', task_priority_enum, server_default='medium', nullable=False),
    )

    op.create_table(
        'rules',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('natural_language', sa.Text(), nullable=False),
        sa.Column('compiled_json', sa.JSON()),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
    )

    op.create_table(
        'flows',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('compiled_json', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
    )

    op.create_table(
        'ai_events',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), sa.ForeignKey('conversations.id')),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
    )

    op.create_table(
        'notifications',
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', notification_type_enum, nullable=False),
        sa.Column('entity_type', notification_entity_enum, nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('seen', sa.Boolean(), server_default='false', nullable=False),
    )
    op.create_index('ix_notifications_user_seen', 'notifications', ['user_id', 'seen', 'created_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('ai_events')
    op.drop_table('flows')
    op.drop_table('rules')
    op.drop_table('tasks')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('contact_settings')
    op.drop_table('contacts')
    op.drop_table('channels')
    op.drop_table('users')

    sa.Enum(name='channel_type').drop(op.get_bind())
    sa.Enum(name='conversation_status').drop(op.get_bind())
    sa.Enum(name='message_direction').drop(op.get_bind())
    sa.Enum(name='task_status').drop(op.get_bind())
    sa.Enum(name='task_priority').drop(op.get_bind())
    sa.Enum(name='notification_type').drop(op.get_bind())
    sa.Enum(name='notification_entity').drop(op.get_bind())
