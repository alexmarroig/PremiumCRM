from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Conversation, Task, User
from db.session import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    priority: str = "medium"
    conversation_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: str | None = None
    priority: str | None = None


@router.get("", response_model=list[dict])
def list_tasks(filter: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Task).filter(Task.user_id == current_user.id)
    today = date.today()
    if filter == "today":
        query = query.filter(Task.due_date == today)
    elif filter == "overdue":
        query = query.filter(Task.due_date < today, Task.status != "done")
    tasks = query.order_by(Task.due_date.asc().nullslast()).all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in tasks
    ]


@router.post("", response_model=dict)
def create_task(payload: TaskCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = Task(
        user_id=current_user.id,
        conversation_id=payload.conversation_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        priority=payload.priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"id": str(task.id), "title": task.title}


@router.patch("/{task_id}", response_model=dict)
def update_task(task_id: str, payload: TaskUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return {"id": str(task.id), "title": task.title, "status": task.status}


@router.post("/{task_id}/complete")
def complete_task(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "done"
    db.commit()
    return {"status": "ok"}
