import asyncio
import uuid

from fastapi import HTTPException
from types import SimpleNamespace

from services.automation import callbacks as callbacks_module
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
