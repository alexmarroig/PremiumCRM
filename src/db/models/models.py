import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


channel_enum = Enum(
    "whatsapp", "instagram", "messenger", "email", "other", name="channel_type"
)
conversation_status_enum = Enum("open", "closed", name="conversation_status")
direction_enum = Enum("inbound", "outbound", name="message_direction")
task_status_enum = Enum("todo", "doing", "done", name="task_status")
task_priority_enum = Enum("low", "medium", "high", name="task_priority")
notification_type_enum = Enum(
    "urgent_message",
    "overdue_task",
    "stalled_lead",
    "rule_match",
    "onboarding",
    name="notification_type",
)
notification_entity_enum = Enum(
    "conversation", "task", "rule", "system", name="notification_entity"
)
user_role_enum = Enum("agent", "manager", "admin", name="user_role")
automation_delivery_status_enum = Enum(
    "pending", "sent", "failed", name="automation_delivery_status"
)
automation_callback_status_enum = Enum(
    "processed", "rejected", name="automation_callback_status"
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(user_role_enum, default="agent", server_default="agent")

    channels = relationship("Channel", back_populates="user")
    contacts = relationship("Contact", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    rules = relationship("Rule", back_populates="user")
    flows = relationship("Flow", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(channel_enum, nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String)

    user = relationship("User", back_populates="channels")
    conversations = relationship("Conversation", back_populates="channel")


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("user_id", "handle", name="uq_contact_handle"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    handle: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}", default=list)

    user = relationship("User", back_populates="contacts")
    settings = relationship("ContactSettings", back_populates="contact", uselist=False)
    conversations = relationship("Conversation", back_populates="contact")


class ContactSettings(Base):
    __tablename__ = "contact_settings"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id"), primary_key=True
    )
    negotiation_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    base_price_default: Mapped[Optional[float]] = mapped_column(Numeric)
    custom_price: Mapped[Optional[float]] = mapped_column(Numeric)
    vip: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    preferred_tone: Mapped[Optional[str]] = mapped_column(String)

    contact = relationship("Contact", back_populates="settings")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_last", "user_id", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("channels.id"), nullable=False)
    status: Mapped[str] = mapped_column(conversation_status_enum, default="open", server_default="open")
    last_message_at: Mapped[Optional[datetime]] = mapped_column()
    unread_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    timeline: Mapped[Optional[dict]] = mapped_column(JSONB)

    user = relationship("User", back_populates="conversations")
    contact = relationship("Contact", back_populates="conversations")
    channel = relationship("Channel", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation", "conversation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(direction_enum, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    channel_message_id: Mapped[Optional[str]] = mapped_column(String)
    ai_classification: Mapped[Optional[dict]] = mapped_column(JSON)

    conversation = relationship("Conversation", back_populates="messages")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "source_event_id", name="uq_tasks_user_source_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("conversations.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(task_status_enum, default="todo", server_default="todo")
    priority: Mapped[str] = mapped_column(task_priority_enum, default="medium", server_default="medium")
    source_event_id: Mapped[Optional[str]] = mapped_column(String)

    user = relationship("User", back_populates="tasks")
    conversation = relationship("Conversation")


class LeadTask(Base):
    __tablename__ = "lead_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(task_priority_enum, default="medium", server_default="medium")
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(task_status_enum, default="todo", server_default="todo")

    conversation = relationship("Conversation")
    assignee = relationship("User")


class InternalComment(Base):
    __tablename__ = "internal_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    conversation = relationship("Conversation")
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("conversations.id"))
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user = relationship("User")
    conversation = relationship("Conversation")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    natural_language: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_json: Mapped[Optional[dict]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user = relationship("User", back_populates="rules")


class Flow(Base):
    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    compiled_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user = relationship("User", back_populates="flows")


class AIEvent(Base):
    __tablename__ = "ai_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("conversations.id"))
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    user = relationship("User")
    conversation = relationship("Conversation")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_seen", "user_id", "seen", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(notification_type_enum, nullable=False)
    entity_type: Mapped[str] = mapped_column(notification_entity_enum, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column()
    seen: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    message: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="notifications")


class AutomationDestination(Base):
    __tablename__ = "automation_destinations"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_automation_destination_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    secret_env_key: Mapped[str] = mapped_column(String, nullable=False)
    secret_masked: Mapped[str] = mapped_column(String, nullable=False)
    secret_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    event_types: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}", default=list)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    deliveries = relationship("AutomationDelivery", back_populates="destination")


class AutomationEvent(Base):
    __tablename__ = "automation_events"
    __table_args__ = (
        Index("ix_automation_events_user_type", "user_id", "type"),
        UniqueConstraint("user_id", "type", "source_event_id", name="uq_automation_event_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    source_event_id: Mapped[Optional[str]] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    user = relationship("User")
    deliveries = relationship("AutomationDelivery", back_populates="event")


class AutomationDelivery(Base):
    __tablename__ = "automation_deliveries"
    __table_args__ = (
        UniqueConstraint("event_id", "destination_id", name="uq_automation_delivery_event_destination"),
        Index("ix_automation_deliveries_status_retry", "status", "next_retry_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_destinations.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_events.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(automation_delivery_status_enum, default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column()

    destination = relationship("AutomationDestination", back_populates="deliveries")
    event = relationship("AutomationEvent", back_populates="deliveries")


class AutomationCallbackEvent(Base):
    __tablename__ = "automation_callback_events"
    __table_args__ = (
        UniqueConstraint("event_id", "destination_id", name="uq_automation_callback_event_destination"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_destinations.id"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(automation_callback_status_enum, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response: Mapped[Optional[dict]] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    destination = relationship("AutomationDestination")
    user = relationship("User")


class AutomationBuilderAutomation(Base):
    __tablename__ = "automation_builder_automations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    flow_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")


class AutomationBuilderRun(Base):
    __tablename__ = "automation_builder_runs"
    __table_args__ = (
        Index("ix_automation_builder_runs_user_event", "user_id", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=None
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    automation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("automation_builder_automations.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    actions_executed: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    error: Mapped[Optional[str]] = mapped_column(Text)

    user = relationship("User")
    automation = relationship("AutomationBuilderAutomation")


# Explicitly define indexes for contacts
Index("ix_contacts_user_handle", Contact.user_id, Contact.handle)
