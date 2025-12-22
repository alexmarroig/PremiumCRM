from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Conversation, User
from db.session import get_db
from services.ai.mock_provider import MockAIProvider

router = APIRouter(prefix="/ai", tags=["ai"])
ai_provider = MockAIProvider()


class MessageBody(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/classify-message")
def classify_message(payload: MessageBody, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convo = None
    history = []
    if payload.conversation_id:
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if convo:
            history = [m.body for m in convo.messages[-5:]]
    result = ai_provider.classify_message(payload.message, history)
    return result


@router.post("/suggest-reply")
def suggest_reply(payload: MessageBody, current_user: User = Depends(get_current_user)):
    return ai_provider.suggest_reply(payload.message)


@router.post("/suggest-price")
def suggest_price(payload: MessageBody, current_user: User = Depends(get_current_user)):
    return ai_provider.suggest_price(payload.message)


@router.post("/suggest-followup")
def suggest_followup(payload: MessageBody, current_user: User = Depends(get_current_user)):
    return ai_provider.suggest_followup(payload.message)
