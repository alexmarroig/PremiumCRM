from datetime import datetime, timedelta, timezone
from typing import Callable, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import AIEvent, Channel, Contact, ContactSettings, Conversation, Message, Notification, Rule, Task, User
from db.session import get_db
from services.ai.mock_provider import MockAIProvider
from services.automation.rules_engine import evaluate_rule
from services.webhooks.normalizers import email, instagram, messenger, whatsapp

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
ai_provider = MockAIProvider()

NORMALIZERS: Dict[str, Callable[[dict], dict]] = {
    "whatsapp": whatsapp.normalize,
    "instagram": instagram.normalize,
    "messenger": messenger.normalize,
    "email": email.normalize,
}


def get_or_create_channel(db: Session, user_id, channel_type: str) -> Channel:
    channel = db.query(Channel).filter(Channel.user_id == user_id, Channel.type == channel_type).first()
    if not channel:
        channel = Channel(user_id=user_id, type=channel_type)
        db.add(channel)
        db.commit()
        db.refresh(channel)
    return channel


def get_or_create_contact(db: Session, user_id, normalized: dict) -> Contact:
    contact = db.query(Contact).filter(Contact.user_id == user_id, Contact.handle == normalized["handle"]).first()
    if contact:
        return contact
    contact = Contact(
        user_id=user_id,
        name=normalized.get("name") or normalized["handle"],
        handle=normalized["handle"],
        avatar_url=normalized.get("avatar_url"),
        tags=[],
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    db.add(ContactSettings(contact_id=contact.id))
    db.commit()
    return contact


def get_or_create_conversation(db: Session, user_id, contact_id, channel_id) -> Conversation:
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.contact_id == contact_id,
            Conversation.channel_id == channel_id,
        )
        .first()
    )
    if convo:
        return convo
    convo = Conversation(user_id=user_id, contact_id=contact_id, channel_id=channel_id, status="open")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.post("/{channel_type}")
def ingest_webhook(channel_type: str, payload: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if channel_type not in NORMALIZERS:
        raise HTTPException(status_code=400, detail="Unsupported channel")
    normalized = NORMALIZERS[channel_type](payload)
    channel = get_or_create_channel(db, current_user.id, channel_type)
    contact = get_or_create_contact(db, current_user.id, normalized)
    conversation = get_or_create_conversation(db, current_user.id, contact.id, channel.id)

    message = Message(
        conversation_id=conversation.id,
        direction="inbound",
        body=normalized["body"],
        raw_payload=payload,
        channel_message_id=normalized.get("channel_message_id"),
    )
    conversation.unread_count += 1
    conversation.last_message_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)

    classification = ai_provider.classify_message(message.body, history=None)
    message.ai_classification = classification
    db.add(AIEvent(user_id=current_user.id, conversation_id=conversation.id, event_type="message.received", payload=classification))

    rules = db.query(Rule).filter(Rule.user_id == current_user.id, Rule.active == True).all()
    for rule in rules:
        if rule.compiled_json and evaluate_rule(rule.compiled_json, message.body):
            db.add(AIEvent(user_id=current_user.id, conversation_id=conversation.id, event_type="rule.matched", payload={"rule_id": str(rule.id)}))
            db.add(
                Notification(
                    user_id=current_user.id,
                    type="rule_match",
                    entity_type="rule",
                    entity_id=rule.id,
                )
            )

    if classification.get("urgency") == "high" or classification.get("sentiment") in {"irritated", "anxious", "frustrated"}:
        db.add(
            Notification(
                user_id=current_user.id,
                type="urgent_message",
                entity_type="conversation",
                entity_id=conversation.id,
            )
        )

    if classification.get("should_create_task"):
        task = Task(
            user_id=current_user.id,
            conversation_id=conversation.id,
            title=f"Follow up with {contact.name}",
            due_date=datetime.now(timezone.utc).date() + timedelta(days=1),
        )
        db.add(task)
        db.add(
            Notification(
                user_id=current_user.id,
                type="overdue_task",
                entity_type="task",
                entity_id=task.id,
            )
        )

    db.commit()
    return {"status": "ok", "normalized": normalized}
