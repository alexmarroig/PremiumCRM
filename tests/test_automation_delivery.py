from datetime import datetime, timezone
from types import SimpleNamespace

import requests

from services.automation.publisher import send_delivery


class DummyDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_send_delivery_success(monkeypatch):
    def fake_post(*args, **kwargs):
        response = SimpleNamespace()
        response.raise_for_status = lambda: None
        return response

    monkeypatch.setenv("AUTOMATION_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("AUTOMATION_DEFAULT_TIMEOUT_SECONDS", "1")
    monkeypatch.setenv("AUTOMATION_REPLAY_WINDOW_SECONDS", "300")
    monkeypatch.setenv("AUTOMATION_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("AUTOMATION_DESTINATION_SECRET_TEST", "secret")
    monkeypatch.setattr(requests, "post", fake_post)

    db = DummyDB()
    event = SimpleNamespace(
        id="event-1",
        user_id="tenant-1",
        type="message.sent",
        payload={"message_id": "1"},
        occurred_at=datetime.now(timezone.utc),
    )
    destination = SimpleNamespace(
        id="dest-1",
        url="https://example.com",
        secret_env_key="AUTOMATION_DESTINATION_SECRET_TEST",
    )
    delivery = SimpleNamespace(
        attempts=0,
        last_error=None,
        next_retry_at=None,
        status="pending",
    )

    assert send_delivery(db, delivery, destination, event) is True
    assert delivery.status == "sent"


def test_send_delivery_failure_sets_retry(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setenv("AUTOMATION_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("AUTOMATION_DEFAULT_TIMEOUT_SECONDS", "1")
    monkeypatch.setenv("AUTOMATION_REPLAY_WINDOW_SECONDS", "300")
    monkeypatch.setenv("AUTOMATION_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("AUTOMATION_ENABLED", "true")
    monkeypatch.setenv("AUTOMATION_DESTINATION_SECRET_TEST", "secret")
    monkeypatch.setattr(requests, "post", fake_post)

    db = DummyDB()
    event = SimpleNamespace(
        id="event-1",
        user_id="tenant-1",
        type="message.sent",
        payload={"message_id": "1"},
        occurred_at=datetime.now(timezone.utc),
    )
    destination = SimpleNamespace(
        id="dest-1",
        url="https://example.com",
        secret_env_key="AUTOMATION_DESTINATION_SECRET_TEST",
    )
    delivery = SimpleNamespace(
        attempts=0,
        last_error=None,
        next_retry_at=None,
        status="pending",
    )

    assert send_delivery(db, delivery, destination, event) is False
    assert delivery.status in {"pending", "failed"}
    assert delivery.attempts == 1
    if delivery.status == "pending":
        assert delivery.next_retry_at is not None
