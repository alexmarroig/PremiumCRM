# Alfred CRM Backend

Production-grade FastAPI backend for the Alfred premium AI CRM. Ships with multi-tenant support, JWT auth, AI mock provider, webhook ingestion, automation jobs, and PostgreSQL persistence.

## Stack
- Python 3.12
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 + Alembic
- PostgreSQL
- JWT (access + refresh)
- APScheduler background jobs
- Docker + docker-compose

## Getting started
1. Copy `.env.example` to `.env` and adjust secrets if needed.
2. Run migrations and start services:
```bash
docker-compose up --build
```
3. Apply migrations inside the container if not auto-run:
```bash
docker-compose exec api alembic upgrade head
```
4. Seed demo data (creates demo@alfred.ai / password):
```bash
docker-compose exec api python scripts/seed_demo.py
```

### AI provider modes
- `AI_PROVIDER_BACKEND=mock` (default): heuristic-only responses without external signals.
- `AI_PROVIDER_BACKEND=income`: uses `IncomeAwareAIProvider` to blend message tone with mocked income/size signals to tailor classifications and price guidance.

When using the income-aware mode, ensure you capture user consent for financial inference and surface how signals are combined. The provider intentionally excludes biometric/location data and expects upstream systems to honor opt-in/out preferences.

API will be available at `http://localhost:8000/api/v1`. OpenAPI docs at `/api/v1/openapi.json`.

## Common commands
```bash
make dev           # docker-compose up
make run           # local uvicorn
make migrate       # run Alembic migrations
make seed          # seed demo data
make test          # run pytest suite
```

## Sample requests
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d '{"name":"Ada","email":"ada@example.com","password":"secret"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"ada@example.com","password":"secret"}'

# Get conversations
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/v1/conversations

# Ingest webhook (email example)
curl -X POST http://localhost:8000/api/v1/webhooks/email -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d '{"message_id":"123","from":"customer@example.com","from_name":"Customer","body":"Need pricing","sent_at":"2024-05-01T12:00:00Z"}'
```

## Tests
Run pytest locally or in the container: `make test`.

## Notes
- AI provider defaults to mock heuristics; can be swapped via `services/ai/provider.py` interface.
- All records are scoped per-user; queries filter on `user_id`.
- Background jobs emit overdue and stalled lead notifications hourly/daily.
