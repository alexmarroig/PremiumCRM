from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from db.models import AutomationBuilderAutomation, AutomationBuilderRun
from services.automation.callbacks import execute_action


class TriggerMessageIngested(BaseModel):
    type: Literal["message.ingested"]
    params: dict[str, Any] | None = None


class TriggerConversationUpdated(BaseModel):
    type: Literal["conversation.updated"]
    params: dict[str, Any] | None = None


class TriggerNoReplyAfter(BaseModel):
    type: Literal["no_reply_after"]
    params: dict[str, Any] | None = None


TriggerType = Annotated[
    TriggerMessageIngested | TriggerConversationUpdated | TriggerNoReplyAfter,
    Field(discriminator="type"),
]


class ConditionContainsText(BaseModel):
    type: Literal["contains_text"]
    text: str


class ConditionUrgencyIs(BaseModel):
    type: Literal["urgency_is"]
    value: Literal["low", "medium", "high"]


class ConditionLeadScoreGte(BaseModel):
    type: Literal["lead_score_gte"]
    value: float


class ConditionChannelIs(BaseModel):
    type: Literal["channel_is"]
    value: Literal["whatsapp", "instagram", "messenger", "email", "other"]


ConditionType = Annotated[
    ConditionContainsText | ConditionUrgencyIs | ConditionLeadScoreGte | ConditionChannelIs,
    Field(discriminator="type"),
]


class ActionCreateTask(BaseModel):
    type: Literal["create_task"]
    title: str
    priority: Literal["low", "medium", "high"] = "medium"


class ActionUpdateConversationStatus(BaseModel):
    type: Literal["update_conversation_status"]
    status: Literal["open", "closed"]


class ActionAddInternalComment(BaseModel):
    type: Literal["add_internal_comment"]
    text: str


class ActionSendMessage(BaseModel):
    type: Literal["send_message"]
    text: str
    channel: Literal["whatsapp", "instagram", "messenger", "email", "other"] | None = None
    conversation_id: UUID | None = None


class ActionUpdateContact(BaseModel):
    type: Literal["update_contact"]
    patch: dict[str, Any]


ActionType = Annotated[
    ActionCreateTask
    | ActionUpdateConversationStatus
    | ActionAddInternalComment
    | ActionSendMessage
    | ActionUpdateContact,
    Field(discriminator="type"),
]


class AutomationFlow(BaseModel):
    trigger: TriggerType
    conditions: list[ConditionType] = []
    actions: list[ActionType]

    @model_validator(mode="after")
    def validate_actions(self) -> "AutomationFlow":
        if not self.actions:
            raise ValueError("At least one action is required")
        return self


class AutomationBuilderCreate(BaseModel):
    name: str
    enabled: bool = True
    flow_json: AutomationFlow


class AutomationBuilderPatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    flow_json: AutomationFlow | None = None


class AutomationBuilderTestRunInput(BaseModel):
    event_type: str
    event_payload: dict[str, Any]


def _extract_lead_score(event_payload: dict[str, Any]) -> float | None:
    lead = event_payload.get("lead") if isinstance(event_payload.get("lead"), dict) else None
    if lead and lead.get("score") is not None:
        return float(lead.get("score"))
    if event_payload.get("lead_score") is not None:
        return float(event_payload.get("lead_score"))
    classification = event_payload.get("classification") if isinstance(event_payload.get("classification"), dict) else None
    if classification and classification.get("affordability_score") is not None:
        return float(classification.get("affordability_score"))
    return None


def evaluate_conditions_detailed(
    conditions: list[ConditionType], event_payload: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    message_text = str(event_payload.get("message", {}).get("text") or event_payload.get("body") or "")
    urgency = event_payload.get("urgency")
    if urgency is None:
        urgency = (event_payload.get("classification") or {}).get("urgency") if isinstance(event_payload.get("classification"), dict) else None
    channel_type = None
    channel = event_payload.get("channel")
    if isinstance(channel, dict):
        channel_type = channel.get("type")
    elif isinstance(channel, str):
        channel_type = channel

    lead_score = _extract_lead_score(event_payload)
    details: list[dict[str, Any]] = []

    for condition in conditions:
        passed = True
        if condition.type == "contains_text":
            passed = condition.text.lower() in message_text.lower()
        elif condition.type == "urgency_is":
            passed = urgency == condition.value
        elif condition.type == "lead_score_gte":
            passed = lead_score is not None and lead_score >= condition.value
        elif condition.type == "channel_is":
            passed = channel_type == condition.value

        details.append({"condition": condition.model_dump(mode="json"), "passed": passed})
        if not passed:
            return False, details
    return True, details


def evaluate_conditions(conditions: list[ConditionType], event_payload: dict[str, Any]) -> bool:
    matched, _ = evaluate_conditions_detailed(conditions, event_payload)
    return matched


def _resolve_conversation_id(action: ActionType, event_payload: dict[str, Any]) -> UUID | None:
    if isinstance(action, ActionSendMessage) and action.conversation_id:
        return action.conversation_id
    convo_id = event_payload.get("conversation_id")
    if convo_id:
        return UUID(str(convo_id))
    return None


def execute_actions(
    db: Session,
    user_id: UUID,
    actions: list[ActionType],
    event_payload: dict[str, Any],
    source_event_id: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    executed: list[dict[str, Any]] = []
    results: dict[str, Any] = {}

    for action in actions:
        conversation_id = event_payload.get("conversation_id")
        if action.type == "create_task":
            payload = {
                "title": action.title,
                "priority": action.priority,
                "conversation_id": conversation_id,
                "source_event_id": source_event_id,
            }
            result = execute_action(db, str(user_id), "create_task", payload)
        elif action.type == "update_conversation_status":
            payload = {"conversation_id": conversation_id, "status": action.status}
            result = execute_action(db, str(user_id), "update_conversation_status", payload)
        elif action.type == "add_internal_comment":
            payload = {"conversation_id": conversation_id, "body": action.text}
            result = execute_action(db, str(user_id), "add_internal_comment", payload)
        elif action.type == "send_message":
            payload = {
                "conversation_id": str(action.conversation_id) if action.conversation_id else conversation_id,
                "text": action.text,
                "channel": action.channel,
            }
            result = execute_action(db, str(user_id), "send_message", payload)
        elif action.type == "update_contact":
            payload = {
                "contact_id": event_payload.get("contact_id"),
                "fields": action.patch,
            }
            result = execute_action(db, str(user_id), "update_contact", payload)
        else:
            continue

        executed.append({"type": action.type, "result": result})
        results.setdefault("actions", []).append({"type": action.type, **result})

    return executed, results


def run_automation(
    db: Session,
    user_id: UUID,
    automation: AutomationBuilderAutomation,
    event_type: str,
    event_payload: dict[str, Any],
    source_event_id: str | None = None,
) -> dict[str, Any]:
    flow = AutomationFlow.model_validate(automation.flow_json)
    trigger_matched = flow.trigger.type == event_type
    conditions_matched, condition_results = evaluate_conditions_detailed(flow.conditions, event_payload)
    matched = trigger_matched and conditions_matched
    actions_executed: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    error: str | None = None

    try:
        if matched:
            actions_executed, results = execute_actions(
                db,
                user_id,
                flow.actions,
                event_payload,
                source_event_id=source_event_id,
            )
        db.add(
            AutomationBuilderRun(
                user_id=user_id,
                automation_id=automation.id,
                event_type=event_type,
                event_payload=event_payload,
                matched=matched,
                actions_executed=actions_executed,
                error=error,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        error = str(exc)
        db.add(
            AutomationBuilderRun(
                user_id=user_id,
                automation_id=automation.id,
                event_type=event_type,
                event_payload=event_payload,
                matched=matched,
                actions_executed=actions_executed,
                error=error,
            )
        )
        db.commit()
        raise

    return {
        "matched": matched,
        "trigger_matched": trigger_matched,
        "condition_results": condition_results,
        "actions_executed": actions_executed,
        "results": results,
    }


def run_enabled_automations(
    db: Session,
    user_id: UUID,
    event_type: str,
    event_payload: dict[str, Any],
    source_event_id: str | None = None,
) -> list[dict[str, Any]]:
    automations = (
        db.query(AutomationBuilderAutomation)
        .filter(
            AutomationBuilderAutomation.user_id == user_id,
            AutomationBuilderAutomation.enabled == True,
            AutomationBuilderAutomation.trigger_type == event_type,
        )
        .all()
    )
    outputs: list[dict[str, Any]] = []
    for automation in automations:
        outputs.append(
            run_automation(
                db=db,
                user_id=user_id,
                automation=automation,
                event_type=event_type,
                event_payload=event_payload,
                source_event_id=source_event_id,
            )
        )
    return outputs
