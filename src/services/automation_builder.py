from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from db.models import AutomationBuilderAutomation, AutomationBuilderRun
from services.automation.callbacks import execute_action
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import (
    AutomationBuilderAutomation,
    AutomationBuilderRun,
    Contact,
    Conversation,
    InternalComment,
    Message,
    Task,
)


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


def get_builder_catalog() -> dict[str, Any]:
    return {
        "version": "mvp-1",
        "ui": {
            "mode": "guided",
            "specialization": "atendimento",
            "frontend_ready": True,
            "frontend_hint": "Vercel-friendly JSON contract",
        },
        "triggers": [
            {"type": "message.ingested", "label": "Mensagem recebida", "params_schema": {}},
            {"type": "conversation.updated", "label": "Conversa atualizada", "params_schema": {}},
            {
                "type": "no_reply_after",
                "label": "Sem resposta após tempo",
                "params_schema": {"minutes": {"type": "number", "required": True}},
            },
        ],
        "conditions": [
            {
                "type": "contains_text",
                "label": "Contém texto",
                "fields": {"text": {"type": "string", "required": True}},
            },
            {
                "type": "urgency_is",
                "label": "Urgência é",
                "fields": {
                    "value": {
                        "type": "enum",
                        "required": True,
                        "options": ["low", "medium", "high"],
                    }
                },
            },
            {
                "type": "lead_score_gte",
                "label": "Lead score >=",
                "fields": {"value": {"type": "number", "required": True}},
            },
            {
                "type": "channel_is",
                "label": "Canal é",
                "fields": {
                    "value": {
                        "type": "enum",
                        "required": True,
                        "options": ["whatsapp", "instagram", "messenger", "email", "other"],
                    }
                },
            },
        ],
        "actions": [
            {
                "type": "create_task",
                "label": "Criar tarefa",
                "fields": {
                    "title": {"type": "string", "required": True},
                    "priority": {
                        "type": "enum",
                        "required": False,
                        "default": "medium",
                        "options": ["low", "medium", "high"],
                    },
                },
            },
            {
                "type": "update_conversation_status",
                "label": "Atualizar status da conversa",
                "fields": {
                    "status": {
                        "type": "enum",
                        "required": True,
                        "options": ["open", "closed"],
                    }
                },
            },
            {
                "type": "add_internal_comment",
                "label": "Adicionar comentário interno",
                "fields": {"text": {"type": "string", "required": True}},
            },
            {
                "type": "send_message",
                "label": "Enviar mensagem",
                "fields": {
                    "text": {"type": "string", "required": True},
                    "channel": {
                        "type": "enum",
                        "required": False,
                        "options": ["whatsapp", "instagram", "messenger", "email", "other"],
                    },
                    "conversation_id": {"type": "uuid", "required": False},
                },
            },
            {
                "type": "update_contact",
                "label": "Atualizar contato",
                "fields": {"patch": {"type": "object", "required": True}},
            },
        ],
    }


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
def evaluate_conditions(conditions: list[ConditionType], event_payload: dict[str, Any]) -> bool:
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

    for condition in conditions:
        if condition.type == "contains_text" and condition.text.lower() not in message_text.lower():
            return False
        if condition.type == "urgency_is" and urgency != condition.value:
            return False
        if condition.type == "lead_score_gte" and (lead_score is None or lead_score < condition.value):
            return False
        if condition.type == "channel_is" and channel_type != condition.value:
            return False
    return True


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

        if action.type == "create_task":
            task = Task(
                user_id=user_id,
                conversation_id=_resolve_conversation_id(action, event_payload),
                title=action.title,
                priority=action.priority,
                source_event_id=source_event_id,
            )
            try:
                with db.begin_nested():
                    db.add(task)
                    db.flush()
                    executed.append({"type": "create_task", "task_id": str(task.id)})
                    results.setdefault("tasks", []).append(str(task.id))
            except IntegrityError:
                executed.append({"type": "create_task", "skipped": "duplicate_source_event"})
        elif action.type == "update_conversation_status":
            conversation_id = _resolve_conversation_id(action, event_payload)
            if conversation_id:
                convo = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
                    .first()
                )
                if convo:
                    convo.status = action.status
                    executed.append({"type": "update_conversation_status", "conversation_id": str(convo.id), "status": action.status})
                    results["conversation_status"] = action.status
        elif action.type == "add_internal_comment":
            conversation_id = _resolve_conversation_id(action, event_payload)
            if conversation_id:
                comment = InternalComment(conversation_id=conversation_id, user_id=user_id, text=action.text)
                db.add(comment)
                db.flush()
                executed.append({"type": "add_internal_comment", "comment_id": str(comment.id)})
                results.setdefault("comments", []).append(str(comment.id))
        elif action.type == "send_message":
            conversation_id = _resolve_conversation_id(action, event_payload)
            if conversation_id:
                message = Message(
                    conversation_id=conversation_id,
                    direction="outbound",
                    body=action.text,
                    raw_payload={"source": "automation_builder", "channel": action.channel},
                )
                db.add(message)
                convo = (
                    db.query(Conversation)
                    .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
                    .first()
                )
                if convo:
                    convo.last_message_at = datetime.now(timezone.utc)
                db.flush()
                executed.append({"type": "send_message", "message_id": str(message.id)})
                results.setdefault("messages", []).append(str(message.id))
        elif action.type == "update_contact":
            contact_id = event_payload.get("contact_id")
            if contact_id:
                contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()
                if contact:
                    for field, value in action.patch.items():
                        if hasattr(contact, field):
                            setattr(contact, field, value)
                    executed.append({"type": "update_contact", "contact_id": str(contact.id), "patch": action.patch})
                    results["contact_updated"] = str(contact.id)
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
    matched = flow.trigger.type == event_type and evaluate_conditions(flow.conditions, event_payload)
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
        run = AutomationBuilderRun(
            user_id=user_id,
            automation_id=automation.id,
            event_type=event_type,
            event_payload=event_payload,
            matched=matched,
            actions_executed=actions_executed,
            error=error,
        )
        db.add(run)
        db.flush()
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
        run = AutomationBuilderRun(
            user_id=user_id,
            automation_id=automation.id,
            event_type=event_type,
            event_payload=event_payload,
            matched=matched,
            actions_executed=actions_executed,
            error=error,
        )
        db.add(run)
        db.flush()
        db.commit()
        raise

    return {
        "matched": matched,
        "trigger_matched": trigger_matched,
        "condition_results": condition_results,
        "actions_executed": actions_executed,
        "results": results,
        "run_id": str(run.id),
        "run_created_at": run.created_at.isoformat() if run.created_at else None,
    }
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

    return {"matched": matched, "actions_executed": actions_executed, "results": results}


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
