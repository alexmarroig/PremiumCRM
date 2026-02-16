import uuid

from services import automation_builder as ab
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


class DummyDB:
    pass


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


def test_execute_actions_create_task_and_update_conversation_status(monkeypatch):
    user_id = uuid.uuid4()
    calls = []

    def fake_execute_action(db, tenant_id, action, payload):
        calls.append((action, payload))
        if action == "create_task":
            return {"task_id": "task-1"}
        if action == "update_conversation_status":
            return {"conversation_id": payload["conversation_id"], "status": payload["status"]}
        return {"ok": True}

    monkeypatch.setattr(ab, "execute_action", fake_execute_action)

    actions = [
        ActionCreateTask(type="create_task", title="Retornar cliente", priority="high"),
        ActionUpdateConversationStatus(type="update_conversation_status", status="closed"),
    ]
    executed, results = execute_actions(
        db=DummyDB(),
        user_id=user_id,
        actions=actions,
        event_payload={"conversation_id": "conv-1"},
        source_event_id="msg-1",
    )

    assert calls[0][0] == "create_task"
    assert calls[0][1]["source_event_id"] == "msg-1"
    assert calls[1][0] == "update_conversation_status"
    assert executed[0]["type"] == "create_task"
    assert results["actions"][1]["status"] == "closed"
