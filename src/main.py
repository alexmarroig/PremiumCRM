import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.errors import setup_exception_handlers
from core.logging import setup_logging
from core.security import TokenError, decode_token
from db.models import AuditLog
from db.session import SessionLocal
from services.ai import get_ai_provider
from services.automation.scheduler import create_scheduler
from api.routers import (
    ai,
    automations,
    automation_builder,
    auth,
    channels,
    contacts,
    conversations,
    flows,
    internal_comments,
    leads,
    me,
    messages,
    notifications,
    rules,
    search,
    tasks,
    webhooks,
)

settings = get_settings()
setup_logging(settings.log_level)
app = FastAPI(title=settings.app_name, version="1.0.0", openapi_url="/api/v1/openapi.json")
setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/api/v1"):
        return response

    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]

    if not token:
        return response

    try:
        user_id = decode_token(token, expected_type="access")
    except TokenError:
        return response

    conversation_id = None
    segments = request.url.path.strip("/").split("/")
    if "conversations" in segments:
        idx = segments.index("conversations")
        if len(segments) > idx + 1:
            conversation_id = segments[idx + 1]
    elif "comments" in segments and "internal" in segments:
        idx = segments.index("comments")
        if len(segments) > idx + 1:
            conversation_id = segments[idx + 1]

    db = SessionLocal()
    try:
        if conversation_id:
            try:
                conversation_id = uuid.UUID(conversation_id)
            except ValueError:
                conversation_id = None
        db.add(
            AuditLog(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                conversation_id=conversation_id,
            )
        )
        db.commit()
    finally:
        db.close()

    return response


@app.on_event("startup")
def startup_event():
    scheduler = create_scheduler()
    scheduler.start()
    app.state.ai_provider = get_ai_provider()


@app.get("/health")
def health():
    return {"status": "ok"}


api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(me.router, prefix=api_prefix)
app.include_router(automations.router, prefix=api_prefix)
app.include_router(automation_builder.router, prefix=api_prefix)
app.include_router(channels.router, prefix=api_prefix)
app.include_router(conversations.router, prefix=api_prefix)
app.include_router(messages.router, prefix=api_prefix)
app.include_router(contacts.router, prefix=api_prefix)
app.include_router(tasks.router, prefix=api_prefix)
app.include_router(rules.router, prefix=api_prefix)
app.include_router(flows.router, prefix=api_prefix)
app.include_router(ai.router, prefix=api_prefix)
app.include_router(ai.router_ia, prefix=api_prefix)
app.include_router(webhooks.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(search.router, prefix=api_prefix)
app.include_router(leads.router, prefix=api_prefix)
app.include_router(internal_comments.router, prefix=api_prefix)

# Compatibility prefix for integrations expecting /v1/* (without /api).
v1_compat_prefix = "/v1"
app.include_router(automations.router, prefix=v1_compat_prefix)
