from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import Flow, User
from db.session import get_db
from services.automation.rules_engine import simulate_flow, validate_flow_schema

router = APIRouter(prefix="/flows", tags=["flows"])


class FlowCreate(BaseModel):
    name: str
    description: str | None = None
    compiled_json: dict
    active: bool = True


class FlowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    compiled_json: dict | None = None
    active: bool | None = None


class FlowSimulationRequest(BaseModel):
    message_text: str
    sentiment: str | None = None
    intent: str | None = None


@router.get("", response_model=list[dict])
def list_flows(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flows = db.query(Flow).filter(Flow.user_id == current_user.id).order_by(Flow.created_at.desc()).all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "compiled_json": f.compiled_json,
            "active": f.active,
        }
        for f in flows
    ]


@router.post("", response_model=dict)
def create_flow(payload: FlowCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = Flow(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        compiled_json=payload.compiled_json,
        active=payload.active,
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return {"id": str(flow.id), "name": flow.name}


@router.patch("/{flow_id}")
def update_flow(flow_id: str, payload: FlowUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = db.query(Flow).filter(Flow.id == flow_id, Flow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(flow, field, value)
    db.commit()
    return {"status": "ok"}


@router.post("/{flow_id}/validate", response_model=dict)
def validate_flow(flow_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = db.query(Flow).filter(Flow.id == flow_id, Flow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    valid, errors = validate_flow_schema(flow.compiled_json)
    return {"valid": valid, "errors": errors}


@router.post("/{flow_id}/simulate", response_model=dict)
def simulate(flow_id: str, payload: FlowSimulationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = db.query(Flow).filter(Flow.id == flow_id, Flow.user_id == current_user.id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    result = simulate_flow(flow.compiled_json, payload.model_dump())
    return result
