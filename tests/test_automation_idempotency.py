from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from services.automation.publisher import create_event


class FakeQuery:
    def __init__(self, existing):
        self.existing = existing

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.existing


class FakeDB:
    def __init__(self, existing):
        self.existing = existing
        self.commit_calls = 0
        self.rollback_calls = 0

    def add(self, item):
        self.added = item

    def commit(self):
        self.commit_calls += 1
        if self.commit_calls == 1:
            raise IntegrityError("stmt", "params", Exception("duplicate"))

    def rollback(self):
        self.rollback_calls += 1

    def query(self, model):
        return FakeQuery(self.existing)

    def refresh(self, item):
        return None


def test_create_event_returns_existing_on_duplicate_source_event_id():
    existing = SimpleNamespace(id="existing-event")
    db = FakeDB(existing=existing)

    result = create_event(
        db,
        tenant_id="tenant-1",
        event_type="message.ingested",
        payload={"message_id": "m-1"},
        source_event_id="provider-msg-1",
    )

    assert result is existing
    assert db.rollback_calls == 1
