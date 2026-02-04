from datetime import date, datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from core.logging import get_logger
from db.models import Conversation, Notification, Task
from db.session import SessionLocal
from services.automation.publisher import process_pending_deliveries

logger = get_logger(__name__)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_overdue_tasks, "interval", hours=1)
    scheduler.add_job(check_stalled_leads, "interval", days=1)
    scheduler.add_job(process_pending_deliveries, "interval", minutes=1)
    return scheduler


def check_overdue_tasks() -> None:
    db: Session = SessionLocal()
    try:
        today = date.today()
        tasks = db.query(Task).filter(Task.due_date < today, Task.status != "done").all()
        for task in tasks:
            db.add(
                Notification(
                    user_id=task.user_id,
                    type="overdue_task",
                    entity_type="task",
                    entity_id=task.id,
                )
            )
        db.commit()
    finally:
        db.close()


def check_stalled_leads() -> None:
    db: Session = SessionLocal()
    try:
        threshold = datetime.now(timezone.utc) - timedelta(days=3)
        conversations = db.query(Conversation).filter(
            Conversation.last_message_at < threshold,
            Conversation.unread_count > 0,
        ).all()
        for convo in conversations:
            db.add(
                Notification(
                    user_id=convo.user_id,
                    type="stalled_lead",
                    entity_type="conversation",
                    entity_id=convo.id,
                )
            )
        db.commit()
    finally:
        db.close()
