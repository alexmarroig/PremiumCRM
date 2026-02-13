from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import AutomationBuilderAutomation, User
from db.session import get_db
from services.automation_builder import (
    AutomationBuilderCreate,
    AutomationBuilderPatch,
    AutomationBuilderTestRunInput,
    run_automation,
)

router = APIRouter(prefix="/automation-builder/automations", tags=["automation-builder"])


@router.get("", response_model=list[dict])
def list_automations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    automations = (
        db.query(AutomationBuilderAutomation)
        .filter(AutomationBuilderAutomation.user_id == current_user.id)
        .order_by(AutomationBuilderAutomation.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "enabled": a.enabled,
            "trigger_type": a.trigger_type,
            "flow_json": a.flow_json,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }
        for a in automations
    ]


@router.post("", response_model=dict)
def create_automation(
    payload: AutomationBuilderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    automation = AutomationBuilderAutomation(
        user_id=current_user.id,
        name=payload.name,
        enabled=payload.enabled,
        trigger_type=payload.flow_json.trigger.type,
        flow_json=payload.flow_json.model_dump(mode="json"),
    )
    db.add(automation)
    db.commit()
    db.refresh(automation)
    return {
        "id": str(automation.id),
        "name": automation.name,
        "enabled": automation.enabled,
        "trigger_type": automation.trigger_type,
        "flow_json": automation.flow_json,
    }


@router.get("/{automation_id}", response_model=dict)
def get_automation(automation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    automation = (
        db.query(AutomationBuilderAutomation)
        .filter(AutomationBuilderAutomation.id == automation_id, AutomationBuilderAutomation.user_id == current_user.id)
        .first()
    )
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return {
        "id": str(automation.id),
        "name": automation.name,
        "enabled": automation.enabled,
        "trigger_type": automation.trigger_type,
        "flow_json": automation.flow_json,
        "created_at": automation.created_at,
        "updated_at": automation.updated_at,
    }


@router.patch("/{automation_id}", response_model=dict)
def patch_automation(
    automation_id: str,
    payload: AutomationBuilderPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    automation = (
        db.query(AutomationBuilderAutomation)
        .filter(AutomationBuilderAutomation.id == automation_id, AutomationBuilderAutomation.user_id == current_user.id)
        .first()
    )
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        automation.name = changes["name"]
    if "enabled" in changes:
        automation.enabled = changes["enabled"]
    if "flow_json" in changes:
        automation.flow_json = payload.flow_json.model_dump(mode="json")
        automation.trigger_type = payload.flow_json.trigger.type

    db.commit()
    db.refresh(automation)
    return {
        "id": str(automation.id),
        "name": automation.name,
        "enabled": automation.enabled,
        "trigger_type": automation.trigger_type,
        "flow_json": automation.flow_json,
    }


@router.delete("/{automation_id}")
def delete_automation(automation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    automation = (
        db.query(AutomationBuilderAutomation)
        .filter(AutomationBuilderAutomation.id == automation_id, AutomationBuilderAutomation.user_id == current_user.id)
        .first()
    )
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    db.delete(automation)
    db.commit()
    return {"status": "ok"}


@router.post("/{automation_id}/test-run", response_model=dict)
def test_run_automation(
    automation_id: str,
    payload: AutomationBuilderTestRunInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    automation = (
        db.query(AutomationBuilderAutomation)
        .filter(AutomationBuilderAutomation.id == automation_id, AutomationBuilderAutomation.user_id == current_user.id)
        .first()
    )
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    output = run_automation(
        db=db,
        user_id=current_user.id,
        automation=automation,
        event_type=payload.event_type,
        event_payload=payload.event_payload,
        source_event_id=str(payload.event_payload.get("message_id")) if payload.event_payload.get("message_id") else None,
    )
    return output
