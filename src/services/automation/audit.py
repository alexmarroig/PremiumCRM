import uuid
from typing import Optional

from sqlalchemy.orm import Session

from db.models import AuditLog


def record_automation_audit(
    db: Session,
    user_id: str,
    action: str,
    metadata: Optional[dict] = None,
    conversation_id: Optional[str] = None,
) -> None:
    suffix = ""
    if metadata:
        summary = ",".join(f"{k}={v}" for k, v in sorted(metadata.items()))
        suffix = f" | {summary}"

    convo_uuid = None
    if conversation_id:
        try:
            convo_uuid = uuid.UUID(str(conversation_id))
        except ValueError:
            convo_uuid = None

    if not hasattr(db, "add"):
        return

    db.add(
        AuditLog(
            user_id=user_id,
            action=f"{action}{suffix}",
            conversation_id=convo_uuid,
        )
    )
    db.commit()
