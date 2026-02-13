import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import get_settings
from db.models import (
    AutomationCallbackEvent,
    AutomationDestination,
    Contact,
    Conversation,
    InternalComment,
    Message,
    Task,
)
from services.automation.publisher import publish_event
from services.automation.signing import (
    decode_signature_header,
    is_timestamp_within_window,
    resolve_destination_secret,
    verify_signature,
)


def _require_field(payload: dict, field: str) -> Any:
    if field not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing field: {field}")
    return payload[field]


def validate_callback_request(
    db: Session,
    raw_body: bytes,
    payload: dict,
    signature: str,
    timestamp: str,
    destination_id: str,
    event_id: str,
) -> AutomationDestination:
    settings = get_settings()
    if not settings.automation_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Automation disabled")
    if not is_timestamp_within_window(timestamp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale timestamp")

    destination = (
        db.query(AutomationDestination)
        .filter(AutomationDestination.id == destination_id)
        .first()
    )
    if not destination or not destination.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")

    tenant_id = str(_require_field(payload, "tenant_id"))
    if str(destination.user_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    event_id_value = event_id or payload.get("event_id")
    if not event_id_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event_id")

    secret = resolve_destination_secret(destination)
    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing destination secret")

    signature_value = decode_signature_header(signature)
    if not verify_signature(secret, timestamp, event_id_value, tenant_id, raw_body, signature_value):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    return destination


def record_callback_event(
    db: Session,
    tenant_id: str,
    destination_id: str,
    event_id: str,
    payload: dict,
    status_value: str,
    response: Optional[dict] = None,
) -> AutomationCallbackEvent:
    record = AutomationCallbackEvent(
        user_id=tenant_id,
        destination_id=destination_id,
        event_id=event_id,
        status=status_value,
        payload=payload,
        response=response,
        received_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def execute_action(db: Session, tenant_id: str, action: str, payload: dict) -> Dict[str, Any]:
    if action == "create_task":
        due_at = payload.get("due_at")
        if isinstance(due_at, str):
            try:
                due_at = datetime.fromisoformat(due_at).date()
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid due_at format")
        task = Task(
            user_id=tenant_id,
            conversation_id=payload.get("conversation_id"),
            title=_require_field(payload, "title"),
            description=payload.get("description"),
            due_date=due_at,
            priority=payload.get("priority") or "medium",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        publish_event(
            db,
            tenant_id,
            "task.created",
            {"task_id": str(task.id), "conversation_id": task.conversation_id, "title": task.title},
            source_event_id=str(task.id),
        )
        return {"task_id": str(task.id)}

    if action == "update_conversation_status":
        conversation_id = _require_field(payload, "conversation_id")
        status_value = _require_field(payload, "status")
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == tenant_id)
            .first()
        )
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        convo.status = status_value
        db.commit()
        publish_event(
            db,
            tenant_id,
            "conversation.updated",
            {
                "conversation_id": str(convo.id),
                "status": convo.status,
                "channel": str(convo.channel_id),
            },
            source_event_id=f"{convo.id}:{convo.status}",
        )
        return {"conversation_id": str(convo.id), "status": convo.status}

    if action == "add_internal_comment":
        conversation_id = _require_field(payload, "conversation_id")
        body = _require_field(payload, "body")
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == tenant_id)
            .first()
        )
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        comment = InternalComment(
            conversation_id=convo.id,
            user_id=tenant_id,
            text=body,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return {"comment_id": str(comment.id)}

    if action == "send_message":
        conversation_id = _require_field(payload, "conversation_id")
        text = _require_field(payload, "text")
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == tenant_id)
            .first()
        )
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        message = Message(
            conversation_id=convo.id,
            direction="outbound",
            body=text,
            raw_payload={"source": "automation"},
        )
        convo.last_message_at = datetime.now(timezone.utc)
        db.add(message)
        db.commit()
        db.refresh(message)
        publish_event(
            db,
            tenant_id,
            "message.sent",
            {
                "message_id": str(message.id),
                "conversation_id": str(convo.id),
                "body": message.body,
                "channel": str(convo.channel_id),
            },
            source_event_id=str(message.id),
        )
        return {"message_id": str(message.id)}

    if action == "update_contact":
        contact_id = _require_field(payload, "contact_id")
        fields = _require_field(payload, "fields")
        contact = (
            db.query(Contact)
            .filter(Contact.id == contact_id, Contact.user_id == tenant_id)
            .first()
        )
        if not contact:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        for field, value in fields.items():
            if hasattr(contact, field):
                setattr(contact, field, value)
        db.commit()
        publish_event(
            db,
            tenant_id,
            "contact.updated",
            {
                "contact_id": str(contact.id),
                "fields": fields,
            },
            source_event_id=f"{contact.id}:{hashlib.sha256(json.dumps(fields, sort_keys=True).encode('utf-8')).hexdigest()}",
        )
        return {"contact_id": str(contact.id)}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action")
