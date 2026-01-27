from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Channel, Contact, Conversation, Message, User
from db.session import get_db

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    query: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    urgency: str | None = None,
    score_gt: float | None = Query(None, alias="score_gt"),
    last_contact_days: int | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query_set = (
        db.query(Conversation)
        .join(Contact)
        .join(Channel)
        .outerjoin(Message)
        .filter(Conversation.user_id == current_user.id)
        .distinct()
    )
    if status:
        query_set = query_set.filter(Conversation.status == status)
    if channel:
        query_set = query_set.filter(Channel.type == channel)
    if query:
        search = f"%{query}%"
        query_set = query_set.filter(
            (Contact.name.ilike(search))
            | (Contact.handle.ilike(search))
            | (Message.body.ilike(search))
        )
    if last_contact_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=last_contact_days)
        query_set = query_set.filter(Conversation.last_message_at >= cutoff)

    conversations = query_set.order_by(Conversation.last_message_at.desc().nullslast()).all()

    results = []
    for convo in conversations:
        last_msg = convo.messages[-1] if convo.messages else None
        ai_cls = last_msg.ai_classification if last_msg else None
        urgency_value = ai_cls.get("urgency") if ai_cls else None
        score_value = ai_cls.get("affordability_score") if ai_cls else None

        if urgency and urgency_value != urgency:
            continue
        if score_gt is not None and (score_value is None or float(score_value) <= score_gt):
            continue

        results.append(
            {
                "conversation_id": str(convo.id),
                "contact_id": str(convo.contact.id),
                "contact_name": convo.contact.name,
                "channel": convo.channel.type,
                "status": convo.status,
                "last_message": last_msg.body if last_msg else None,
                "last_message_at": convo.last_message_at.isoformat() if convo.last_message_at else None,
                "urgency": urgency_value,
                "score": score_value,
            }
        )

    total = len(results)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    paginated = results[start:end]

    return {
        "results": paginated,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }
