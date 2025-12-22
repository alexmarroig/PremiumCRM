from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Rule, User
from db.session import get_db
from services.automation.rules_engine import compile_rule, evaluate_rule

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleCreate(BaseModel):
    natural_language: str
    active: bool = True


class RuleUpdate(BaseModel):
    natural_language: str | None = None
    active: bool | None = None
    compiled_json: dict | None = None


@router.get("", response_model=list[dict])
def list_rules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rules = db.query(Rule).filter(Rule.user_id == current_user.id).order_by(Rule.created_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "natural_language": r.natural_language,
            "compiled_json": r.compiled_json,
            "active": r.active,
        }
        for r in rules
    ]


@router.post("", response_model=dict)
def create_rule(payload: RuleCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rule = Rule(user_id=current_user.id, natural_language=payload.natural_language, active=payload.active)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": str(rule.id), "natural_language": rule.natural_language}


@router.post("/{rule_id}/compile", response_model=dict)
def compile_rule_endpoint(rule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.user_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.compiled_json = compile_rule(rule.natural_language)
    db.commit()
    return {"id": str(rule.id), "compiled_json": rule.compiled_json}


@router.patch("/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.user_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    return {"status": "ok"}


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id, Rule.user_id == current_user.id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "deleted"}
