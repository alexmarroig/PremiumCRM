import asyncio
import uuid

from fastapi import HTTPException
from types import SimpleNamespace

from services.automation import callbacks as callbacks_module
from api.routers.automations import DebugSignRequest, automation_callback, debug_sign_callback
from services.automation.callbacks import execute_action, validate_callback_request


class FakeQuery:
    def __init__(self, instance):
        self.instance = instance

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.instance


class FakeDB:
    def __init__(self, conversation=None):
        self.conversation = conversation
        self.added = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def refresh(self, item):
        return None

    def query(self, model):
        if model.__name__ == "Conversation":
            return FakeQuery(self.conversation)
        return FakeQuery(None)


def test_execute_action_create_task(monkeypatch):
    monkeypatch.setattr(callbacks_module, "publish_event", lambda *args, **kwargs: None)
    db = FakeDB()
    result = execute_action(
        db,
        tenant_id=str(uuid.uuid4()),
        action="create_task",
        payload={"title": "Follow up"},
    )
    assert "task_id" in result
    assert db.added


def test_execute_action_update_conversation_status(monkeypatch):
    monkeypatch.setattr(callbacks_module, "publish_event", lambda *args, **kwargs: None)
    conversation = SimpleNamespace(id=str(uuid.uuid4()), user_id="tenant-1", status="open", channel_id=str(uuid.uuid4()))
    db = FakeDB(conversation=conversation)
    result = execute_action(
        db,
        tenant_id="tenant-1",
        action="update_conversation_status",
        payload={"conversation_id": conversation.id, "status": "closed"},
    )
    assert result["status"] == "closed"
    assert conversation.status == "closed"


def test_validate_callback_request_rejects_stale_timestamp(monkeypatch):
    monkeypatch.setenv("AUTOMATION_ENABLED", "true")
    monkeypatch.setattr(callbacks_module, "is_timestamp_within_window", lambda *_: False)

    try:
        validate_callback_request(
            db=FakeDB(),
            raw_body=b"{}",
            payload={"tenant_id": "tenant-1", "event_id": "evt-1"},
            signature="sig",
            timestamp="0",
            destination_id="dest-1",
            event_id="evt-1",
        )
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Stale timestamp"
    else:
        raise AssertionError("Expected HTTPException")


class FakeCallbackQuery:
    def __init__(self, existing):
        self.existing = existing

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.existing


class FakeCallbackDB(FakeDB):
    def __init__(self, existing):
        super().__init__()
        self.existing = existing

    def query(self, model):
        if model.__name__ in {"AutomationCallbackEvent", "AutomationDestination"}:
            return FakeCallbackQuery(self.existing)
        return FakeCallbackQuery(None)


class FakeRequest:
    def __init__(self, payload, headers):
        self._payload = payload
        self.headers = headers

    async def body(self):
        import json

        return json.dumps(self._payload).encode("utf-8")

    async def json(self):
        return self._payload


def test_automation_callback_idempotent_short_circuit(monkeypatch):
    existing = SimpleNamespace(response={"task_id": "t-1"})
    db = FakeCallbackDB(existing=existing)

    monkeypatch.setattr(
        "api.routers.automations.validate_callback_request",
        lambda **kwargs: SimpleNamespace(id="dest-1"),
    )

    req = FakeRequest(
        payload={"tenant_id": "tenant-1", "action": "create_task", "event_id": "evt-1", "payload": {"title": "x"}},
        headers={"X-Automation-Timestamp": "1", "X-Automation-Signature": "sig", "X-Automation-Destination-Id": "dest-1", "X-Automation-Event-Id": "evt-1"},
    )

    result = asyncio.run(automation_callback(req, db))
    assert result.ok is True
    assert result.action_result == {"task_id": "t-1"}


def test_debug_sign_callback_requires_flag(monkeypatch):
    monkeypatch.setenv("AUTOMATION_DEBUG_ENABLED", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")

    user = SimpleNamespace(id="tenant-1", role="admin")
    db = FakeCallbackDB(existing=SimpleNamespace(user_id="tenant-1", secret_env_key="X", secret_encrypted=""))

    try:
        debug_sign_callback(
            DebugSignRequest(destination_id="dest-1", body={"tenant_id": "tenant-1"}, timestamp="1", event_id="evt-1"),
            current_user=user,
            db=db,
        )
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected HTTPException")


def test_debug_sign_callback_returns_signature(monkeypatch):
    monkeypatch.setenv("AUTOMATION_DEBUG_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEST_SECRET", "super-secret")

    destination = SimpleNamespace(id="dest-1", user_id="tenant_abc", secret_env_key="DEST_SECRET", secret_encrypted="")
    user = SimpleNamespace(id="tenant_abc", role="admin")
    db = FakeCallbackDB(existing=destination)

    response = debug_sign_callback(
        DebugSignRequest(
            destination_id="dest-1",
            body={"tenant_id": "tenant_abc", "action": "create_task", "payload": {"title": "Ligar para cliente"}},
            timestamp="1700000000",
            event_id="evt_123",
        ),
        current_user=user,
        db=db,
    )

    assert response.base_string.startswith("1700000000.evt_123.tenant_abc.")
    assert response.signature_expected == "098db21286883fa0f8368d83f132ca655f2fd8bb4d4841d10c1b06604e61cc37"
