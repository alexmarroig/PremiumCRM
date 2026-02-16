import uuid
from contextlib import contextmanager

from services.automation_builder import (
    AutomationFlow,
    ActionCreateTask,
    ActionUpdateConversationStatus,
    ConditionContainsText,
    ConditionUrgencyIs,
    TriggerMessageIngested,
    evaluate_conditions,
    execute_actions,
)
from db.models import Conversation


class FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.items[0] if self.items else None


class FakeDB:
    def __init__(self, conversation):
        self.added = []
        self.conversation = conversation

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if hasattr(item, "id") and getattr(item, "id") is None:
                item.id = uuid.uuid4()

    @contextmanager
    def begin_nested(self):
        yield

    def query(self, model):
        if model.__name__ == "Conversation":
            return FakeQuery([self.conversation])
        return FakeQuery([])


def test_flow_schema_validation_requires_actions():
    try:
        AutomationFlow(trigger=TriggerMessageIngested(type="message.ingested"), actions=[])
        assert False, "Flow sem ações deveria falhar"
    except ValueError:
        assert True


def test_conditions_contains_text_and_urgency_is():
    conditions = [
        ConditionContainsText(type="contains_text", text="pix"),
        ConditionUrgencyIs(type="urgency_is", value="high"),
    ]
    assert evaluate_conditions(conditions, {"body": "Olá, aceita PIX?", "urgency": "high"}) is True
    assert evaluate_conditions(conditions, {"body": "Olá", "urgency": "high"}) is False


def test_execute_actions_create_task_and_update_conversation_status():
    user_id = uuid.uuid4()
    conversation = Conversation(id=uuid.uuid4(), user_id=user_id, contact_id=uuid.uuid4(), channel_id=uuid.uuid4(), status="open")
    db = FakeDB(conversation)

    actions = [
        ActionCreateTask(type="create_task", title="Retornar cliente", priority="high"),
        ActionUpdateConversationStatus(type="update_conversation_status", status="closed"),
    ]
    executed, results = execute_actions(
        db=db,
        user_id=user_id,
        actions=actions,
        event_payload={"conversation_id": str(conversation.id)},
        source_event_id="msg-1",
    )

    assert any(a["type"] == "create_task" for a in executed)
    assert any(a["type"] == "update_conversation_status" and a["status"] == "closed" for a in executed)
    assert results["conversation_status"] == "closed"
    assert conversation.status == "closed"
