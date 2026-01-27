from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import require_roles
from db.models import Conversation, InternalComment, User
from db.session import get_db

router = APIRouter(prefix="/internal", tags=["internal"])


class InternalCommentCreate(BaseModel):
    text: str


@router.post("/comments/{conversation_id}")
def add_internal_comment(
    conversation_id: str,
    payload: InternalCommentCreate,
    current_user: User = Depends(require_roles("agent", "manager", "admin")),
    db: Session = Depends(get_db),
):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    comment = InternalComment(
        conversation_id=convo.id,
        user_id=current_user.id,
        text=payload.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id": str(comment.id),
        "conversation_id": str(convo.id),
        "user_id": str(current_user.id),
        "text": comment.text,
        "created_at": comment.created_at.isoformat(),
    }
