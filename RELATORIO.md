# RELATORIO — Discovery backend Alfred + plano Activepieces

## Etapa 0 — Onde está o backend
- **Pasta backend:** `src/` (FastAPI app), com testes em `tests/`.
- **Stack:** Python + FastAPI + Pydantic v2 + SQLAlchemy + Alembic + Postgres + APScheduler.
- **Entrypoint:** `src/main.py` (`FastAPI(...)`, include_router, startup scheduler).
- **Execução local:** `make run`, `make dev` (docker-compose), `make migrate`, `make test`.
- **Deploy/container:** `Dockerfile`, `docker-compose.yml`, `README.production.md`.

## Etapa 1 — Inventário completo

### A) Arquitetura
- **Auth:** JWT access+refresh (`/auth/login`, `/auth/refresh`) com `type=access|refresh` no token; validação em `api/deps.py`.
- **RBAC:** `require_roles('agent','manager','admin')`.
- **Multi-tenant:** isolamento por `user_id` em queries e no hub de automações (`tenant_id` validado contra destination owner).
- **Banco/ORM/migration:** PostgreSQL + SQLAlchemy models (`src/db/models/models.py`) + Alembic (`src/db/migrations/versions/*`).
- **Jobs:** APScheduler em startup (`check_overdue_tasks`, `check_stalled_leads`, `process_pending_deliveries`).

### B) Modelos de dados principais
- `users`: conta, role, credenciais.
- `channels`: canal por tenant (whatsapp/instagram/messenger/email...).
- `contacts` + `contact_settings`: cliente e preferências.
- `conversations`: estado da conversa, unread, timeline.
- `messages`: inbound/outbound, body, payload bruto, classificação AI.
- `tasks` e `lead_tasks`: tarefas gerais e por lead.
- `rules` e `flows`: automações/regras e fluxos compilados.
- `notifications`, `ai_events`, `internal_comments`, `audit_logs`.
- Automations hub:
  - `automation_destinations`
  - `automation_events` (inclui `source_event_id`)
  - `automation_deliveries`
  - `automation_callback_events`

### C) Endpoints (inventário resumido)
Comando usado para extração total: script de introspecção FastAPI (seção comandos).

**Auth pública:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

**Webhooks/automação (auth):**
- `POST /api/v1/webhooks/{channel_type}` (ingestão inbound por canal)
- `POST /api/v1/automations/destinations`
- `GET /api/v1/automations/destinations`
- `PATCH /api/v1/automations/destinations/{destination_id}`
- `DELETE /api/v1/automations/destinations/{destination_id}`
- `POST /api/v1/automations/callbacks`
- aliases compatíveis: `/v1/automations/*`

**Mensagens e CRM (auth):**
- `POST /api/v1/conversations/{conversation_id}/messages` (send outbound)
- Endpoints de contatos, conversas, tarefas, regras, flows, notificações, busca e IA.

### D) Engine atual de automação
- **Rules engine:** `services/automation/rules_engine.py` (`compile_rule`, `evaluate_rule`, `simulate_flow`, `validate_flow_schema`).
- **NL -> JSON:** criação de flow por prompt em `api/routers/ai.py` / provider AI.
- **Execução de ações externas:**
  - outbound: `services/automation/publisher.py` (`publish_event`)
  - inbound: `services/automation/callbacks.py` (`execute_action`)

### E) Observabilidade
- **Error handling:** `core/errors.py` + handlers globais.
- **Logging:** setup em `core/logging.py`.
- **Audit middleware:** em `main.py` para requests `/api/v1` autenticados.
- **Automations audit:** esta implementação adiciona registros de `automation_event_sent` e `automation_callback_executed` em `audit_logs`.
- **Correlation id:** callback usa `event_id/correlation_id` para dedupe e rastreio.

## Etapa 2 — Design da integração Activepieces

### 1) Outbound events (Alfred -> Activepieces)
- Eventos mínimos: `message.ingested`, `conversation.updated`, `task.created`, `task.completed`, `contact.updated`, `lead.score_changed` (+ `message.sent`).
- Payload padrão:
```json
{
  "event_id": "<uuid>",
  "tenant_id": "<tenant_uuid>",
  "occurred_at": "<iso8601>",
  "type": "message.ingested",
  "payload": {"...": "..."}
}
```
- Headers: `X-Alfred-Event-Id`, `X-Alfred-Tenant-Id`, `X-Alfred-Timestamp`, `X-Alfred-Signature`.
- Assinatura: HMAC-SHA256 sobre `timestamp.event_id.tenant_id.raw_body`.
- Anti-replay: `AUTOMATION_REPLAY_WINDOW_SECONDS` (default 300s).

### 2) Destinations CRUD por tenant
- Endpoints já existentes e mantidos, com alias `/v1`.
- Campos: `name`, `url`, `secret`, `enabled`, `event_types`, timestamps.
- Segurança do secret:
  - `secret_masked` (exibição)
  - `secret_encrypted` (persistência criptografada com key de env)
  - fallback env key por destination.

### 3) Delivery log + retry
- `automation_deliveries`: status, attempts, last_error, next_retry_at.
- Envio imediato + retry com backoff (`60, 300, 900, 3600, 21600`).
- Worker a cada 1 min via APScheduler (`process_pending_deliveries`).

### 4) Inbound callbacks (Activepieces -> Alfred)
- Endpoint: `POST /api/v1/automations/callbacks` (alias `/v1/...`).
- Segurança: valida assinatura, timestamp, tenant ownership, destination habilitado.
- Payload suportado:
  - `tenant_id`, `correlation_id|event_id`, `action`, `params|payload`
- Ações MVP:
  - `create_task`
  - `update_conversation_status`
  - `add_internal_comment`
  - `send_message`
  - `update_contact`
- Idempotência callback: dedupe por `(destination_id, event_id)` com retorno da resposta já persistida.

## Etapa 3 — Implementação realizada
1. **Migrations/Models**
   - `0005`: `automation_events.source_event_id` + unique constraint.
   - `0006`: `automation_destinations.secret_encrypted`.
2. **Services**
   - `signing.py`: assinatura, anti-replay, criptografia/decriptografia de secret, resolução de secret por destination.
   - `publisher.py`: idempotência outbound (`source_event_id`), retry e auditoria de envio.
   - `callbacks.py`: validação HMAC+tenant+timestamp, execução de ações e dedupe.
   - `audit.py`: registro em `audit_logs` para automações.
3. **Routers**
   - Destinations CRUD e callbacks suportando `params`/`correlation_id`.
   - Alias `/v1/automations/*` adicionado.
4. **Testes**
   - assinatura/anti-replay
   - idempotência callback (short-circuit)
   - retry/backoff
   - idempotência de criação de evento outbound
5. **Docs**
   - README com variáveis env, curl de destination, callback assinado e quickstart de 10 min.

## Etapa 4 — Plano incremental de hardening (próximos passos)
1. Trocar criptografia leve de secrets por KMS/Vault gerenciado.
2. Adicionar bloqueio SSRF (deny private CIDR) em URLs de destination.
3. Padronizar `X-Correlation-Id` em todos os routers e logs estruturados JSON.
4. Expor endpoint de inspeção de deliveries (filtro por status/destination) para UI operacional.
5. Adicionar métricas Prometheus (latência de delivery, taxa de falha, retries por tenant).

## Comandos executados
```bash
# Discovery (routers, webhook ingest, send_message, rules engine)
rg -n "APIRouter\(|include_router|@router\.(get|post|patch|delete)|JWT|refresh|require_roles|tenant|publish_event|process_pending_deliveries|create_scheduler|rules_engine|normalize\(" src/api src/services src/core src/main.py

# Listar endpoints FastAPI
cd src && python - <<'PY'
from main import app
for r in sorted(app.routes, key=lambda x: x.path):
    methods=','.join(sorted(m for m in (r.methods or []) if m not in {'HEAD','OPTIONS'}))
    if methods:
        print(f"{methods:12} {r.path}")
PY

# Dependências e jobs
rg -n "fastapi|pydantic|sqlalchemy|alembic|psycopg|apscheduler|python-jose|passlib|requests" requirements.txt
rg -n "add_job\(|process_pending_deliveries|check_overdue_tasks|check_stalled_leads" src/services/automation/scheduler.py src/main.py
```
