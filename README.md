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

# Fetch onboarding notification (returned right after first login)
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/v1/notifications | jq
```

## Onboarding
- No primeiro token emitido (registro ou login inicial) o backend cria uma notificação de boas-vindas atrelada ao usuário.
- Essa notificação é do tipo `onboarding`, possui `entity_type` `system` e inclui uma mensagem explicando que tokens e integrações básicas (webhooks, notificações automáticas) já estão configurados.
- O frontend deve chamar `/api/v1/notifications` logo após autenticação e exibir essa mensagem imediatamente ao usuário.

## Tests
Run pytest locally or in the container: `make test`.

## Notes
- AI provider defaults to mock heuristics; can be swapped via `services/ai/provider.py` interface.
- All records are scoped per-user; queries filter on `user_id`.
- Background jobs emit overdue and stalled lead notifications hourly/daily.
- Automation Hub emite eventos para destinos externos (Activepieces) e recebe callbacks assinados.

## Automation Hub (Activepieces)
O backend expõe um hub de automações que envia eventos do CRM para webhooks do Activepieces e recebe callbacks assinados com ações a executar no CRM.

### Configuração (env)
```
AUTOMATION_ENABLED=true
AUTOMATION_DEFAULT_TIMEOUT_SECONDS=10
AUTOMATION_MAX_ATTEMPTS=8
AUTOMATION_REPLAY_WINDOW_SECONDS=300
AUTOMATION_RATE_LIMIT_PER_MINUTE=60
AUTOMATION_SECRET_ENCRYPTION_KEY=<chave-forte-para-criptografar-secrets>
```

### Endpoints de automação
Compatíveis em ambos os prefixos:
- `/api/v1/automations/*`
- `/v1/automations/*` (alias para integrações externas)

### Destinos (webhooks outbound)
Crie um destino por tenant em `POST /api/v1/automations/destinations`.

Campos:
- `name`
- `url`
- `secret`
- `enabled`
- `event_types` (`*` ou lista de tipos)

O segredo é:
- mascarado no banco (`secret_masked`)
- persistido também em formato criptografado (`secret_encrypted`) usando `AUTOMATION_SECRET_ENCRYPTION_KEY`

Headers enviados para o Activepieces:
- `X-Alfred-Signature` (HMAC-SHA256)
- `X-Alfred-Event-Id`
- `X-Alfred-Tenant-Id`
- `X-Alfred-Timestamp` (epoch seconds)

Payload padrão:
```json
{
  "event_id": "...",
  "tenant_id": "...",
  "occurred_at": "2024-07-15T12:00:00Z",
  "type": "message.ingested",
  "payload": { "..." }
}
```

Idempotência outbound:
- O publisher aceita `source_event_id` opcional para evitar duplicação de eventos quando a mesma ação é reprocessada.
- Existe restrição única por tenant/tipo/fonte (`user_id`, `type`, `source_event_id`) na tabela `automation_events`.


### Callbacks (webhooks inbound)
Endpoint: `POST /api/v1/automations/callbacks`

Headers esperados:
- `X-Automation-Signature` (HMAC-SHA256)
- `X-Automation-Event-Id`
- `X-Automation-Destination-Id`
- `X-Automation-Timestamp` (epoch seconds)

Payload mínimo:
```json
{
  "tenant_id": "...",
  "correlation_id": "cbk-evt-001",
  "action": "create_task",
  "params": { "title": "Follow up" }
}
```

Ações suportadas:
- `create_task`
- `update_conversation_status`
- `add_internal_comment`
- `send_message`
- `update_contact`

Exemplo de callback assinado para o Alfred:
```bash
curl -X POST http://localhost:8000/api/v1/automations/callbacks \
  -H "Content-Type: application/json" \
  -H "X-Automation-Signature: <hmac_sha256_hex>" \
  -H "X-Automation-Event-Id: cbk-evt-001" \
  -H "X-Automation-Destination-Id: <destination_uuid>" \
  -H "X-Automation-Timestamp: <epoch_seconds>" \
  -d '{
    "tenant_id": "<tenant_uuid>",
    "action": "create_task",
    "payload": {"title": "Retornar cliente", "priority": "high"}
  }'
```

### Checklist E2E (Alfred <-> Activepieces)
1. Criar destino em `/api/v1/automations/destinations` com `event_types` relevantes (ex.: `message.ingested`, `task.created`).
2. No Activepieces, criar flow com **Webhook Trigger** apontando para a URL de destino configurada no Alfred.
3. Enviar mensagem inbound para Alfred (`/api/v1/webhooks/{channel}`) e validar recebimento no trigger do Activepieces.
4. No flow, adicionar ação HTTP para `POST /api/v1/automations/callbacks` com headers assinados.
5. Validar execução da ação no Alfred (ex.: tarefa criada, contato atualizado).
6. Simular falha no destino e confirmar retries automáticos (`automation_deliveries.status=pending` com `next_retry_at`).
7. Repetir callback com mesmo `event_id` e confirmar comportamento idempotente (resposta reaproveitada).

### Subindo o Activepieces localmente
Há um `docker-compose` auxiliar em `ops/activepieces/docker-compose.yml`. Suba com:
```bash
docker-compose -f ops/activepieces/docker-compose.yml up
```
Depois configure um workflow no Activepieces apontando o webhook de entrada para o Alfred, e use o endpoint de callback do Alfred como action HTTP no fluxo.
