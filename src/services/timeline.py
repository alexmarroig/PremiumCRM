from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models import AIEvent, Conversation, LeadTask, Task


TIMELINE_TYPE_MAP = {
    "rule.matched": "rule",
    "message.received": "message",
    "summary.generated": "ai_summary",
    "flow.created": "ai_flow",
    "voice.transcribed": "ai_voice",
}


def _format_dt(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


def build_conversation_timeline(db: Session, conversation: Conversation) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for message in conversation.messages:
        items.append(
            {
                "type": "ai_reply" if message.direction == "outbound" else "message",
                "direction": message.direction,
                "body": message.body,
                "created_at": _format_dt(message.created_at),
                "ai_classification": message.ai_classification,
            }
        )

    for task in db.query(Task).filter(Task.conversation_id == conversation.id).all():
        items.append(
            {
                "type": "task",
                "source": "general",
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": _format_dt(task.created_at),
            }
        )

    for task in db.query(LeadTask).filter(LeadTask.conversation_id == conversation.id).all():
        items.append(
            {
                "type": "task",
                "source": "lead",
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                "created_at": _format_dt(task.created_at),
            }
        )

    for event in db.query(AIEvent).filter(AIEvent.conversation_id == conversation.id).all():
        items.append(
            {
                "type": TIMELINE_TYPE_MAP.get(event.event_type, "ai_event"),
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": _format_dt(event.created_at),
            }
        )

    items.sort(key=lambda entry: entry.get("created_at") or "")
    return items
