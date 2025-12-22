from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Notification, User
from db.session import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[dict])
def list_notifications(seen: bool | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if seen is not None:
        query = query.filter(Notification.seen == seen)
    items = query.order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "entity_type": n.entity_type,
            "entity_id": str(n.entity_id),
            "seen": n.seen,
            "created_at": n.created_at,
        }
        for n in items
    ]


@router.post("/{notification_id}/seen")
def mark_seen(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Not found")
    notif.seen = True
    db.commit()
    return {"status": "ok"}
