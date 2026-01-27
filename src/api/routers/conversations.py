from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Channel, Contact, ContactSettings, Conversation, LeadTask, Message, User
from db.session import get_db
from services.timeline import build_conversation_timeline

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationSummary(BaseModel):
    id: str
    contact_name: str
    contact_avatar_url: Optional[str] = None
    channel_type: str
    unread_count: int
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    sentiment: Optional[str]
    urgency: Optional[str]


class ConversationDetail(BaseModel):
    id: str
    status: str
    contact: dict
    channel: dict
    unread_count: int
    last_message_at: Optional[datetime]
    contact_settings: Optional[dict]


class ConversationPatch(BaseModel):
    status: str


class LeadTaskPayload(BaseModel):
    title: str | None = None
    priority: str = "medium"
    due_date: date | None = None
    assignee_id: str | None = None
    status: str | None = None


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    q: Optional[str] = None,
    unread_only: bool = Query(False),
    sentiment: Optional[str] = None,
    urgency: Optional[str] = None,
):
    query = db.query(Conversation).join(Contact).join(Channel).filter(Conversation.user_id == current_user.id)
    if status:
        query = query.filter(Conversation.status == status)
    if channel:
        query = query.filter(Channel.type == channel)
    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))
    if unread_only:
        query = query.filter(Conversation.unread_count > 0)

    conversations = query.order_by(Conversation.last_message_at.desc().nullslast()).all()
    summaries: list[ConversationSummary] = []
    for convo in conversations:
        last_msg = convo.messages[-1] if convo.messages else None
        ai_cls = last_msg.ai_classification if last_msg else None
        summaries.append(
            ConversationSummary(
                id=str(convo.id),
                contact_name=convo.contact.name,
                contact_avatar_url=convo.contact.avatar_url,
                channel_type=convo.channel.type,
                unread_count=convo.unread_count,
                last_message=last_msg.body if last_msg else None,
                last_message_at=convo.last_message_at,
                sentiment=ai_cls.get("sentiment") if ai_cls else None,
                urgency=ai_cls.get("urgency") if ai_cls else None,
            )
        )
    return summaries


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    settings = convo.contact.settings
    contact_payload = {
        "id": str(convo.contact.id),
        "name": convo.contact.name,
        "avatar_url": convo.contact.avatar_url,
        "handle": convo.contact.handle,
    }
    channel_payload = {"id": str(convo.channel.id), "type": convo.channel.type}
    return ConversationDetail(
        id=str(convo.id),
        status=convo.status,
        contact=contact_payload,
        channel=channel_payload,
        unread_count=convo.unread_count,
        last_message_at=convo.last_message_at,
        contact_settings={
            "negotiation_enabled": settings.negotiation_enabled if settings else False,
            "base_price_default": str(settings.base_price_default) if settings and settings.base_price_default else None,
            "custom_price": str(settings.custom_price) if settings and settings.custom_price else None,
            "vip": settings.vip if settings else False,
            "preferred_tone": settings.preferred_tone if settings else None,
        }
        if settings
        else None,
    )


@router.patch("/{conversation_id}", response_model=ConversationDetail)
def update_conversation(
    conversation_id: str,
    payload: ConversationPatch,
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
    convo.status = payload.status
    db.commit()
    db.refresh(convo)
    return get_conversation(conversation_id, current_user, db)


@router.post("/{conversation_id}/mark-read")
def mark_read(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.unread_count = 0
    db.commit()
    return {"status": "ok"}


@router.post("/{conversation_id}/history")
def conversation_history(
    conversation_id: str,
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
    timeline = build_conversation_timeline(db, convo)
    convo.timeline = {"items": timeline}
    db.commit()
    return {"conversation_id": str(convo.id), "timeline": timeline}


@router.post("/{conversation_id}/tasks")
def manage_lead_tasks(
    conversation_id: str,
    payload: LeadTaskPayload | None = None,
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

    if payload and payload.title:
        lead_task = LeadTask(
            conversation_id=convo.id,
            title=payload.title,
            priority=payload.priority,
            due_date=payload.due_date,
            assignee_id=payload.assignee_id,
            status=payload.status or "todo",
        )
        db.add(lead_task)
        db.commit()
        db.refresh(lead_task)

    tasks = (
        db.query(LeadTask)
        .filter(LeadTask.conversation_id == convo.id)
        .order_by(LeadTask.due_date.asc().nullslast())
        .all()
    )
    return [
        {
            "id": str(task.id),
            "title": task.title,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            "status": task.status,
        }
        for task in tasks
    ]
