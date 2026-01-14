from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.errors import setup_exception_handlers
from core.logging import setup_logging
from services.ai import get_ai_provider
from services.automation.scheduler import create_scheduler
from api.routers import (
    ai,
    auth,
    channels,
    contacts,
    conversations,
    flows,
    me,
    messages,
    notifications,
    rules,
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
app.include_router(channels.router, prefix=api_prefix)
app.include_router(conversations.router, prefix=api_prefix)
app.include_router(messages.router, prefix=api_prefix)
app.include_router(contacts.router, prefix=api_prefix)
app.include_router(tasks.router, prefix=api_prefix)
app.include_router(rules.router, prefix=api_prefix)
app.include_router(flows.router, prefix=api_prefix)
app.include_router(ai.router, prefix=api_prefix)
app.include_router(webhooks.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
