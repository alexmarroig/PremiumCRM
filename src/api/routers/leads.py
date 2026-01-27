from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Contact, Conversation, User
from db.session import get_db
from services.timeline import build_conversation_timeline

router = APIRouter(prefix="/leads", tags=["leads"])


SENTIMENT_SCORES = {
    "positive": 1.0,
    "neutral": 0.0,
    "irritated": -1.0,
    "anxious": -0.5,
    "frustrated": -0.8,
}


@router.get("/{lead_id}/full")
def lead_full(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(Contact)
        .filter(Contact.id == lead_id, Contact.user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.contact_id == contact.id, Conversation.user_id == current_user.id)
        .order_by(Conversation.last_message_at.desc().nullslast())
        .all()
    )

    timeline = []
    score_evolution = []
    sentiment_values = []
    affordability_values = []

    for convo in conversations:
        for message in convo.messages:
            if not message.ai_classification:
                continue
            score = message.ai_classification.get("affordability_score")
            if score is not None:
                score_evolution.append(
                    {
                        "timestamp": message.created_at.isoformat(),
                        "score": float(score),
                    }
                )
                affordability_values.append(float(score))
            sentiment = message.ai_classification.get("sentiment")
            if sentiment in SENTIMENT_SCORES:
                sentiment_values.append(SENTIMENT_SCORES[sentiment])

    if conversations:
        timeline = build_conversation_timeline(db, conversations[0])

    settings = contact.settings
    ticket_values = [
        value
        for value in [
            float(settings.base_price_default) if settings and settings.base_price_default else None,
            float(settings.custom_price) if settings and settings.custom_price else None,
        ]
        if value is not None
    ]
    ticket_medio = mean(ticket_values) if ticket_values else None

    return {
        "lead": {
            "id": str(contact.id),
            "name": contact.name,
            "handle": contact.handle,
            "avatar_url": contact.avatar_url,
            "tags": contact.tags,
        },
        "history": timeline,
        "score_evolution": score_evolution,
        "ticket_medio": ticket_medio,
        "sentimento_medio": mean(sentiment_values) if sentiment_values else None,
        "score_medio": mean(affordability_values) if affordability_values else None,
    }
