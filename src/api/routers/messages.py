from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import AIEvent, Conversation, Message, User
from db.session import get_db
from services.ai.mock_provider import MockAIProvider
from services.automation.events import EventBus

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])


class MessageCreate(BaseModel):
    body: str


class MessageOut(BaseModel):
    id: str
    body: str
    direction: str
    created_at: datetime


@router.get("", response_model=list[MessageOut])
def list_messages(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [
        MessageOut(id=str(m.id), body=m.body, direction=m.direction, created_at=m.created_at)
        for m in messages
    ]


@router.post("", response_model=MessageOut)
def create_message(
    conversation_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = Message(
        conversation_id=convo.id,
        direction="outbound",
        body=payload.body,
        raw_payload={"source": "api"},
    )
    convo.last_message_at = datetime.now(timezone.utc)
    db.add(message)
    db.add(AIEvent(user_id=current_user.id, conversation_id=convo.id, event_type="message.sent", payload={"body": payload.body}))
    db.commit()
    db.refresh(message)
    return MessageOut(id=str(message.id), body=message.body, direction=message.direction, created_at=message.created_at)
