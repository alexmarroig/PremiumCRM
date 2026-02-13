import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import AutomationCallbackEvent, AutomationDestination, User
from db.session import get_db
from services.automation.audit import record_automation_audit
from services.automation.callbacks import execute_action, record_callback_event, validate_callback_request
from services.automation.signing import (
    build_env_key,
    encrypt_secret,
    ensure_secret_env,
    mask_secret,
)

router = APIRouter(prefix="/automations", tags=["automations"])


class DestinationCreate(BaseModel):
    name: str
    url: str
    secret: Optional[str] = None
    secret_env_key: Optional[str] = None
    enabled: bool = True
    event_types: list[str] = Field(default_factory=list)


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    secret_env_key: Optional[str] = None
    enabled: Optional[bool] = None
    event_types: Optional[list[str]] = None


class DestinationResponse(BaseModel):
    id: str
    name: str
    url: str
    secret_masked: str
    secret_env_key: str
    enabled: bool
    event_types: list[str]
    created_at: datetime
    updated_at: datetime


class CallbackRequest(BaseModel):
    tenant_id: str
    action: str
    payload: Optional[dict] = None
    params: Optional[dict] = None
    correlation_id: Optional[str] = None
    event_id: Optional[str] = None
    destination_id: Optional[str] = None


class CallbackResponse(BaseModel):
    ok: bool
    action_result: dict
    correlation_id: str


@router.post("/destinations", response_model=DestinationResponse)
def create_destination(
    payload: DestinationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    destination_id = uuid.uuid4()
    secret_env_key = payload.secret_env_key or build_env_key(str(destination_id))
    secret_value = payload.secret or ""
    if secret_value:
        ensure_secret_env(secret_env_key, secret_value)
    secret_masked_value = mask_secret(secret_value)
    destination = AutomationDestination(
        id=destination_id,
        user_id=current_user.id,
        name=payload.name,
        url=payload.url,
        secret_env_key=secret_env_key,
        secret_masked=secret_masked_value,
        secret_encrypted=encrypt_secret(secret_value),
        enabled=payload.enabled,
        event_types=payload.event_types,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return DestinationResponse(
        id=str(destination.id),
        name=destination.name,
        url=destination.url,
        secret_masked=destination.secret_masked,
        secret_env_key=destination.secret_env_key,
        enabled=destination.enabled,
        event_types=destination.event_types,
        created_at=destination.created_at,
        updated_at=destination.updated_at,
    )


@router.get("/destinations", response_model=list[DestinationResponse])
def list_destinations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(AutomationDestination)
        .filter(AutomationDestination.user_id == current_user.id)
        .order_by(AutomationDestination.created_at.desc())
        .all()
    )
    return [
        DestinationResponse(
            id=str(item.id),
            name=item.name,
            url=item.url,
            secret_masked=item.secret_masked,
            secret_env_key=item.secret_env_key,
            enabled=item.enabled,
            event_types=item.event_types,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.patch("/destinations/{destination_id}", response_model=DestinationResponse)
def update_destination(
    destination_id: str,
    payload: DestinationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    destination = (
        db.query(AutomationDestination)
        .filter(AutomationDestination.id == destination_id, AutomationDestination.user_id == current_user.id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")

    if payload.secret_env_key:
        destination.secret_env_key = payload.secret_env_key
    if payload.secret:
        ensure_secret_env(destination.secret_env_key, payload.secret)
        destination.secret_masked = mask_secret(payload.secret)
        destination.secret_encrypted = encrypt_secret(payload.secret)

    for field, value in payload.model_dump(exclude={"secret", "secret_env_key"}, exclude_unset=True).items():
        setattr(destination, field, value)

    destination.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(destination)
    return DestinationResponse(
        id=str(destination.id),
        name=destination.name,
        url=destination.url,
        secret_masked=destination.secret_masked,
        secret_env_key=destination.secret_env_key,
        enabled=destination.enabled,
        event_types=destination.event_types,
        created_at=destination.created_at,
        updated_at=destination.updated_at,
    )


@router.delete("/destinations/{destination_id}")
def delete_destination(
    destination_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    destination = (
        db.query(AutomationDestination)
        .filter(AutomationDestination.id == destination_id, AutomationDestination.user_id == current_user.id)
        .first()
    )
    if not destination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    db.delete(destination)
    db.commit()
    return {"status": "deleted"}


@router.post("/callbacks", response_model=CallbackResponse)
async def automation_callback(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    payload = await request.json()
    signature = request.headers.get("X-Automation-Signature", "")
    timestamp = request.headers.get("X-Automation-Timestamp", "")
    destination_id = request.headers.get("X-Automation-Destination-Id") or payload.get("destination_id")
    event_id = request.headers.get("X-Automation-Event-Id") or payload.get("event_id") or payload.get("correlation_id")
    if not destination_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing destination_id")

    destination = validate_callback_request(
        db=db,
        raw_body=raw_body,
        payload=payload,
        signature=signature,
        timestamp=timestamp,
        destination_id=destination_id,
        event_id=event_id,
    )

    existing = (
        db.query(AutomationCallbackEvent)
        .filter(
            AutomationCallbackEvent.destination_id == destination.id,
            AutomationCallbackEvent.event_id == event_id,
        )
        .first()
    )
    if existing and existing.response:
        return CallbackResponse(ok=True, action_result=existing.response, correlation_id=event_id)

    tenant_id = str(payload.get("tenant_id"))
    action = payload.get("action")
    action_payload = payload.get("payload") or payload.get("params") or {}

    try:
        result = execute_action(db, tenant_id, action, action_payload)
        record_callback_event(
            db,
            tenant_id,
            str(destination.id),
            event_id,
            payload,
            "processed",
            result,
        )
        record_automation_audit(
            db,
            user_id=tenant_id,
            action="automation_callback_executed",
            metadata={"destination_id": str(destination.id), "event_id": event_id, "callback_action": action},
        )
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AutomationCallbackEvent)
            .filter(
                AutomationCallbackEvent.destination_id == destination.id,
                AutomationCallbackEvent.event_id == event_id,
            )
            .first()
        )
        if existing and existing.response:
            return CallbackResponse(ok=True, action_result=existing.response, correlation_id=event_id)
        raise
    except HTTPException as exc:
        record_callback_event(
            db,
            tenant_id,
            str(destination.id),
            event_id,
            payload,
            "rejected",
            {"error": exc.detail},
        )
        raise

    return CallbackResponse(ok=True, action_result=result, correlation_id=event_id)
