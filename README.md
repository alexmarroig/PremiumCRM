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
AUTOMATION_DEBUG_ENABLED=false
```

### Endpoints de automação
Compatíveis em ambos os prefixos:
- `/api/v1/automations/*`
- `/v1/automations/*` (alias para integrações externas)

### Especificação ÚNICA da assinatura HMAC (callbacks Activepieces -> Alfred)
Use exatamente estes headers:
- `X-Automation-Signature`: assinatura em hex (HMAC-SHA256)
- `X-Automation-Timestamp`: epoch seconds (string)
- `X-Automation-Event-Id`: id único do callback (ex.: `cbk-evt-001`)
- `X-Automation-Destination-Id`: id do destination cadastrado no Alfred

Regras exatas:
1. `timestamp` = `Math.floor(Date.now()/1000).toString()`.
2. `body_json` = `JSON.stringify(body)` (sem espaços).
3. `base_string` = `${timestamp}.${event_id}.${tenant_id}.${body_json}`.
4. `signature` = `HMAC_SHA256_HEX(secret, base_string)`.

Validação no backend:
- comparação da assinatura em **constant time** (`hmac.compare_digest`),
- timestamp dentro de `AUTOMATION_REPLAY_WINDOW_SECONDS`,
- `tenant_id` do body deve bater com owner do destination,
- idempotência por `(destination_id, event_id)`.

Exemplo completo (vetor de teste):
- `secret`: `super-secret`
- `timestamp`: `1700000000`
- `event_id`: `evt_123`
- `tenant_id`: `tenant_abc`
- `body_json`:
```json
{"tenant_id":"tenant_abc","action":"create_task","payload":{"title":"Ligar para cliente"}}
```
- `base_string`:
```text
1700000000.evt_123.tenant_abc.{"tenant_id":"tenant_abc","action":"create_task","payload":{"title":"Ligar para cliente"}}
```
- `signature` esperada:
```text
098db21286883fa0f8368d83f132ca655f2fd8bb4d4841d10c1b06604e61cc37
```

### Debug de assinatura (somente dev/admin)
Endpoint:
- `POST /api/v1/automations/debug/sign`

Regras de proteção:
- retorna 404 em produção,
- requer `AUTOMATION_DEBUG_ENABLED=true`,
- requer usuário com role `admin`.

Input:
```json
{
  "destination_id": "<uuid>",
  "body": {"tenant_id": "<tenant_uuid>", "action": "create_task", "payload": {"title": "x"}},
  "timestamp": "1700000000",
  "event_id": "evt_123"
}
```

Output:
```json
{
  "base_string": "...",
  "signature_expected": "..."
}
```

### Activepieces Flow Recipe (copy/paste)
#### Step 1: Webhook Trigger
- Crie um Flow no Activepieces e adicione um **Webhook Trigger**.
- Copie a URL pública do trigger para registrar no Alfred como destination outbound.

#### Step 2: Code step (JavaScript)
Cole este código no Step “Code” (Node.js):
```javascript
const crypto = require('crypto');

// ===== ENTRADAS (edite só aqui) =====
const SECRET = 'COLE_AQUI_O_SECRET_DO_DESTINATION';
const DESTINATION_ID = 'COLE_AQUI_O_DESTINATION_ID';
const TENANT_ID = 'COLE_AQUI_O_TENANT_ID';
const ACTION = 'create_task';
const PAYLOAD = { title: 'Retornar cliente', priority: 'high' };
// ================================

const timestamp = Math.floor(Date.now() / 1000).toString();
const eventId = `cbk-${Date.now()}`;

const body = {
  tenant_id: TENANT_ID,
  action: ACTION,
  payload: PAYLOAD,
};

const bodyJson = JSON.stringify(body);
const baseString = `${timestamp}.${eventId}.${TENANT_ID}.${bodyJson}`;
const signature = crypto.createHmac('sha256', SECRET).update(baseString).digest('hex');

return {
  body,
  headers: {
    'Content-Type': 'application/json',
    'X-Automation-Signature': signature,
    'X-Automation-Timestamp': timestamp,
    'X-Automation-Event-Id': eventId,
    'X-Automation-Destination-Id': DESTINATION_ID,
  },
};
```

#### Step 3: HTTP Request step
- Method: `POST`
- URL: `https://<alfred>/api/v1/automations/callbacks`
- Headers: usar `{{steps.code.headers}}`
- Body (JSON): usar `{{steps.code.body}}`

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

### Quickstart 10 minutos (Activepieces cloud)
Activepieces alvo: `https://activepieces-latest-nrrb.onrender.com`

1. Faça login/registro no Alfred e copie `access_token`.
2. No Activepieces, crie Flow com Webhook Trigger e copie URL.
3. Registre destination no Alfred:
```bash
curl -X POST http://localhost:8000/api/v1/automations/destinations   -H "Authorization: Bearer <access_token>"   -H "Content-Type: application/json"   -d '{"name":"activepieces-main","url":"<webhook_trigger_url>","secret":"<shared_secret>","enabled":true,"event_types":["message.ingested","task.created","contact.updated"]}'
```
4. No Activepieces, adicione Code step com snippet acima.
5. Adicione HTTP Request step apontando para callback do Alfred.
6. Execute o flow e valide retorno `ok: true`.
7. Verifique resultado no Alfred (`/api/v1/tasks`, `/api/v1/contacts`, etc).
### Subindo o Activepieces localmente
Há um `docker-compose` auxiliar em `ops/activepieces/docker-compose.yml`. Suba com:
```bash
docker-compose -f ops/activepieces/docker-compose.yml up
```
Depois configure um workflow no Activepieces apontando o webhook de entrada para o Alfred, e use o endpoint de callback do Alfred como action HTTP no fluxo.
