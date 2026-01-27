from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.models import AIEvent, Conversation, Flow, User
from db.session import get_db
from services.ai import AIProvider, get_ai_provider

router = APIRouter(prefix="/ai", tags=["ai"])
router_ia = APIRouter(prefix="/ia", tags=["ai"])


def get_configured_ai_provider(request: Request) -> AIProvider:
    provider = getattr(request.app.state, "ai_provider", None)
    if provider is not None:
        return provider
    return get_ai_provider()


class MessageBody(BaseModel):
    message: str
    conversation_id: str | None = None


class SummaryResponse(BaseModel):
    summary: str
    suggestions: list[str]


class FlowCreateRequest(BaseModel):
    prompt: str


class VoiceTranscribeRequest(BaseModel):
    audio_base64: str


class VoiceTTSRequest(BaseModel):
    text: str


@router.post("/classify-message")
def classify_message(
    payload: MessageBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    convo = None
    history = []
    if payload.conversation_id:
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if convo:
            history = [m.body for m in convo.messages[-5:]]
    result = ai_provider.classify_message(payload.message, history)
    return result


@router.post("/suggest-reply")
def suggest_reply(
    payload: MessageBody,
    current_user: User = Depends(get_current_user),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    return ai_provider.suggest_reply(payload.message)


@router.post("/suggest-price")
def suggest_price(
    payload: MessageBody,
    current_user: User = Depends(get_current_user),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    return ai_provider.suggest_price(payload.message)


@router.post("/suggest-followup")
def suggest_followup(
    payload: MessageBody,
    current_user: User = Depends(get_current_user),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    return ai_provider.suggest_followup(payload.message)


@router.post("/summary/{conversation_id}", response_model=SummaryResponse)
@router_ia.post("/summary/{conversation_id}", response_model=SummaryResponse)
def summarize_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        return SummaryResponse(summary="Conversa não encontrada.", suggestions=[])
    messages = [m.body for m in convo.messages]
    result = ai_provider.summarize_conversation(messages)
    db.add(
        AIEvent(
            user_id=current_user.id,
            conversation_id=convo.id,
            event_type="summary.generated",
            payload=result,
        )
    )
    db.commit()
    return SummaryResponse(**result)


@router.post("/flow/create")
@router_ia.post("/flow/create")
def create_flow(
    payload: FlowCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    result = ai_provider.create_flow_from_prompt(payload.prompt)
    flow = Flow(
        user_id=current_user.id,
        name=result.get("name") or "Fluxo Alfred",
        description=result.get("description"),
        compiled_json=result.get("compiled_json") or {},
    )
    db.add(flow)
    db.commit()
    db.refresh(flow)
    db.add(
        AIEvent(
            user_id=current_user.id,
            conversation_id=None,
            event_type="flow.created",
            payload={"prompt": payload.prompt, "flow_id": str(flow.id)},
        )
    )
    db.commit()
    return {"id": str(flow.id), "name": flow.name, "description": flow.description}


@router.post("/voice/transcribe")
@router_ia.post("/voice/transcribe")
def voice_transcribe(
    payload: VoiceTranscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    result = ai_provider.transcribe_audio(payload.audio_base64)
    db.add(
        AIEvent(
            user_id=current_user.id,
            conversation_id=None,
            event_type="voice.transcribed",
            payload=result,
        )
    )
    db.commit()
    return result


@router.post("/voice/tts")
@router_ia.post("/voice/tts")
def voice_tts(
    payload: VoiceTTSRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_provider: AIProvider = Depends(get_configured_ai_provider),
):
    result = ai_provider.synthesize_speech(payload.text)
    db.add(
        AIEvent(
            user_id=current_user.id,
            conversation_id=None,
            event_type="voice.tts",
            payload={"text": payload.text},
        )
    )
    db.commit()
    return result
