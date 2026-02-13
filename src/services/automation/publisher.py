import json
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import get_settings
from db.models import AutomationDelivery, AutomationDestination, AutomationEvent
from db.session import SessionLocal
from services.automation.audit import record_automation_audit
from services.automation.rate_limit import rate_limiter
from services.automation.signing import resolve_destination_secret, sign_payload

RETRY_BACKOFF_SECONDS = [60, 300, 900, 3600, 21600]


def compute_next_retry(attempts: int) -> datetime:
    idx = min(max(attempts - 1, 0), len(RETRY_BACKOFF_SECONDS) - 1)
    return datetime.now(timezone.utc) + timedelta(seconds=RETRY_BACKOFF_SECONDS[idx])


def destination_accepts_event(destination: AutomationDestination, event_type: str) -> bool:
    if not destination.event_types:
        return False
    if "*" in destination.event_types:
        return True
    return event_type in destination.event_types


def create_event(
    db: Session,
    tenant_id: str,
    event_type: str,
    payload: dict,
    occurred_at: Optional[datetime] = None,
    source_event_id: Optional[str] = None,
) -> AutomationEvent:
    event = AutomationEvent(
        user_id=tenant_id,
        type=event_type,
        payload=payload,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        source_event_id=source_event_id,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AutomationEvent)
            .filter(
                AutomationEvent.user_id == tenant_id,
                AutomationEvent.type == event_type,
                AutomationEvent.source_event_id == source_event_id,
            )
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(event)
    return event


def enqueue_deliveries(
    db: Session,
    event: AutomationEvent,
    destinations: Iterable[AutomationDestination],
) -> list[AutomationDelivery]:
    deliveries: list[AutomationDelivery] = []
    for destination in destinations:
        delivery = AutomationDelivery(
            user_id=event.user_id,
            destination_id=destination.id,
            event_id=event.id,
            status="pending",
            attempts=0,
            next_retry_at=datetime.now(timezone.utc),
        )
        delivery.destination = destination
        delivery.event = event
        db.add(delivery)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(delivery)
        deliveries.append(delivery)
    return deliveries


def send_delivery(
    db: Session,
    delivery: AutomationDelivery,
    destination: AutomationDestination,
    event: AutomationEvent,
) -> bool:
    settings = get_settings()
    if not rate_limiter.allow(str(event.user_id)):
        delivery.last_error = "rate_limited"
        delivery.attempts += 1
        delivery.next_retry_at = compute_next_retry(delivery.attempts)
        delivery.status = "pending"
        db.commit()
        return False

    payload = {
        "event_id": str(event.id),
        "tenant_id": str(event.user_id),
        "occurred_at": event.occurred_at.isoformat(),
        "type": event.type,
        "payload": event.payload,
    }
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    secret = resolve_destination_secret(destination)
    if not secret:
        delivery.attempts += 1
        delivery.last_error = "missing_secret"
        delivery.status = "failed"
        delivery.next_retry_at = None
        db.commit()
        return False

    signature = sign_payload(
        secret=secret,
        timestamp=timestamp,
        event_id=str(event.id),
        tenant_id=str(event.user_id),
        body=body,
    )
    headers = {
        "Content-Type": "application/json",
        "X-Alfred-Signature": signature,
        "X-Alfred-Event-Id": str(event.id),
        "X-Alfred-Tenant-Id": str(event.user_id),
        "X-Alfred-Timestamp": timestamp,
    }

    try:
        response = requests.post(
            destination.url,
            data=body,
            headers=headers,
            timeout=settings.automation_default_timeout_seconds,
        )
        response.raise_for_status()
    except Exception as exc:
        delivery.attempts += 1
        delivery.last_error = str(exc)
        if delivery.attempts >= settings.automation_max_attempts:
            delivery.status = "failed"
            delivery.next_retry_at = None
        else:
            delivery.status = "pending"
            delivery.next_retry_at = compute_next_retry(delivery.attempts)
        db.commit()
        return False

    delivery.status = "sent"
    delivery.last_error = None
    delivery.next_retry_at = None
    db.commit()
    record_automation_audit(
        db,
        user_id=str(event.user_id),
        action="automation_event_sent",
        metadata={"destination_id": str(destination.id), "event_id": str(event.id), "event_type": event.type},
    )
    return True


def publish_event(
    db: Session,
    tenant_id: str,
    event_type: str,
    payload: dict,
    source_event_id: Optional[str] = None,
) -> Optional[AutomationEvent]:
    settings = get_settings()
    if not settings.automation_enabled:
        return None

    destinations = (
        db.query(AutomationDestination)
        .filter(AutomationDestination.user_id == tenant_id, AutomationDestination.enabled == True)
        .all()
    )
    if not destinations:
        return None

    eligible = [d for d in destinations if destination_accepts_event(d, event_type)]
    if not eligible:
        return None

    event = create_event(db, tenant_id, event_type, payload, source_event_id=source_event_id)
    deliveries = enqueue_deliveries(db, event, eligible)
    for delivery in deliveries:
        send_delivery(db, delivery, delivery.destination, event)
    return event


def process_pending_deliveries() -> None:
    settings = get_settings()
    if not settings.automation_enabled:
        return

    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        pending = (
            db.query(AutomationDelivery)
            .filter(
                AutomationDelivery.status == "pending",
                AutomationDelivery.next_retry_at <= now,
            )
            .all()
        )
        for delivery in pending:
            event = delivery.event
            destination = delivery.destination
            if not event or not destination or not destination.enabled:
                delivery.status = "failed"
                delivery.last_error = "missing_destination_or_event"
                delivery.next_retry_at = None
                db.commit()
                continue
            send_delivery(db, delivery, destination, event)
    finally:
        db.close()
