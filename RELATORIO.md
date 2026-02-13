# Discovery técnico backend Alfred + plano de integração Activepieces

## 0) Escopo e método
Este discovery foi feito diretamente no código FastAPI/SQLAlchemy/Alembic e nos testes do backend, com foco em autenticação JWT, multi-tenant por `user_id`, pipelines inbound/outbound, engine de regras/flows, jobs background, segurança e observabilidade para integração com Activepieces.

---

## 1) Inventário do backend atual

### 1.1 Stack e entrypoints
- **Stack:** FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + PostgreSQL + APScheduler + JWT HS256 + Requests.
- **Entrypoint principal:** `src/main.py`.
  - Configura CORS e exception handlers.
  - Registra middleware de auditoria por request autenticado (`AuditLog`).
  - Sobe scheduler no startup (`check_overdue_tasks`, `check_stalled_leads`, `process_pending_deliveries`).
  - Inclui routers sob `/api/v1/*`.

### 1.2 Auth (JWT, refresh, roles e tenant)
- **Emissão de token:** `create_access_refresh_tokens` cria par access/refresh com tipo explícito no claim (`type`).
- **Validação:** `decode_token(..., expected_type=...)` valida assinatura e tipo.
- **Refresh:** endpoint `/api/v1/auth/refresh` aceita refresh token e emite novo par.
- **RBAC:** `require_roles` usa enum de role do usuário (`agent|manager|admin`), usado por exemplo no endpoint de comentários internos.
- **Multi-tenant:** isolamento por `user_id` em consultas dos routers/serviços. No Automation Hub, `tenant_id` do payload é validado contra `destination.user_id`.

### 1.3 Modelagem principal (SQLAlchemy)
Entidades centrais:
- CRM: `users`, `channels`, `contacts`, `contact_settings`, `conversations`, `messages`, `tasks`, `lead_tasks`, `rules`, `flows`, `ai_events`, `notifications`, `audit_logs`, `internal_comments`.
- Automation Hub: `automation_destinations`, `automation_events`, `automation_deliveries`, `automation_callback_events`.

Atualização implementada nesta PR:
- `automation_events.source_event_id` + unique `(user_id, type, source_event_id)` para idempotência outbound por fonte.

### 1.4 Pipeline de ingestão (webhooks inbound de canais)
- Endpoint único por canal: `POST /api/v1/webhooks/{channel_type}`.
- Normalizadores por canal: WhatsApp/Instagram/Messenger/Email em `services/webhooks/normalizers`.
- Fluxo:
  1. Normaliza payload.
  2. Resolve/cria `Channel`.
  3. Resolve/cria `Contact` (+ `ContactSettings`).
  4. Resolve/cria `Conversation`.
  5. Cria `Message` inbound.
  6. Classifica com provider AI.
  7. Emite eventos automation (`message.ingested`, `lead.score_changed`, etc.).
  8. Avalia regras (`Rule.compiled_json`) e cria notificações/tarefas quando aplicável.

### 1.5 Pipeline outbound de mensagens
- Endpoint: `POST /api/v1/conversations/{conversation_id}/messages`.
- Valida ownership da conversa (`conversation.user_id == current_user.id`).
- Persiste mensagem `direction=outbound`, registra `AIEvent` e emite `message.sent` no hub de automações.
- Também há ação `send_message` via callback do Activepieces em `services/automation/callbacks.py`.

### 1.6 Engine de regras/flows
- **Rules:** `services/automation/rules_engine.py` com `compile_rule`, `evaluate_rule` e validações.
- **Flows:** `compile_flow_from_prompt` (NL->JSON) via provider AI + endpoints em `api/routers/flows.py`.
- **Execução/simulação:** `simulate_flow`/`validate_flow_schema`.
- **Ponto de plug de ações externas:** Automation Hub (`publish_event` outbound e `execute_action` inbound callback).

---

## 2) O que é necessário para integrar Activepieces (descoberto no código)

### 2.1 Melhor ponto para emitir eventos sem duplicar
- Ponto ideal: **service layer** (`publish_event`) chamado pelos routers/serviços após commit de estado de negócio.
- Para reduzir duplicação em reprocessamento, a PR adiciona `source_event_id` e constraint única por tenant/tipo/fonte.

### 2.2 Idempotência eventos/callbacks
- **Outbound:** agora pode usar `source_event_id` determinístico (ex.: `message.id`, `conversation.id:status`, fingerprint de update de contato).
- **Inbound callbacks:** dedupe já existente por `(destination_id, event_id)` em `automation_callback_events`; se já processado com resposta, endpoint retorna resposta anterior.

### 2.3 Secrets por tenant
- Atual: `secret_env_key` + segredo em env/process memory (`ensure_secret_env`, `os.getenv`).
- Não há vault dedicado.
- Recomendação: migrar para KMS/Vault (AWS KMS, Hashicorp Vault, GCP KMS) com envelope encryption por tenant e rotação de segredo.

### 2.4 Retries e jobs
- APScheduler já existe.
- Retry já roda a cada 1 minuto (`process_pending_deliveries`) com backoff progressivo (`[60,300,900,3600,21600]`) e `automation_max_attempts`.

### 2.5 Logs, auditoria e correlação
- Há middleware de auditoria em `main.py` gravando `AuditLog` por request autenticado.
- Callback usa `event_id` como `correlation_id` funcional.
- Recomendação: padronizar `X-Correlation-Id` em todos ingressos/egressos + logging estruturado em JSON com `tenant_id`, `event_id`, `destination_id`, `delivery_id`.

---

## 3) Design proposto (com justificativa)

### A) Outbound events (Alfred -> Activepieces)
Eventos mínimos (já suportados no backend):
- `message.ingested`
- `message.sent`
- `conversation.updated`
- `task.created`
- `task.completed`
- `contact.updated`

Formato payload padrão:
```json
{
  "event_id": "<uuid>",
  "tenant_id": "<tenant_uuid>",
  "occurred_at": "ISO-8601",
  "type": "message.ingested",
  "payload": {"...": "..."}
}
```

Headers:
- `X-Alfred-Signature` = HMAC-SHA256(hex)
- `X-Alfred-Event-Id`
- `X-Alfred-Tenant-Id`
- `X-Alfred-Timestamp`

Segurança:
- Janela anti-replay configurável (`AUTOMATION_REPLAY_WINDOW_SECONDS`).
- Assinatura inclui `timestamp.event_id.tenant_id.body`.

### B) Destinations CRUD por tenant
- Endpoints já disponíveis em `/api/v1/automations/destinations` (POST/GET/PATCH/DELETE).
- Validações atuais: escopo por tenant, enable flag, filtros de `event_types`.
- Recomendação: validar URL allowlist e bloquear private CIDRs (SSRF hardening).

### C) Deliveries + Retry
- Tabela `automation_deliveries` com status, attempts, error e `next_retry_at`.
- Retry com backoff + rate limit por tenant.
- Job de varredura a cada 1 min já em produção.

### D) Inbound callbacks (Activepieces -> Alfred)
- Endpoint único: `POST /api/v1/automations/callbacks`.
- Ações mínimas já implementadas:
  - `create_task`
  - `update_conversation_status`
  - `add_internal_comment`
  - `send_message`
  - `update_contact`
- Segurança:
  - HMAC obrigatório
  - anti-replay por timestamp
  - tenant enforcement (`payload.tenant_id == destination.user_id`)
  - dedupe por `event_id + destination_id`

---

## 4) Implementação executada nesta PR

### Código
- Adicionada idempotência outbound em `automation_events`:
  - migration Alembic `0005_automation_event_idempotency`.
  - model `AutomationEvent.source_event_id` + unique constraint.
  - `publish_event/create_event` aceitam `source_event_id`.
  - em pontos de emissão críticos foi adicionado `source_event_id` determinístico.

### Testes
- Novo teste de idempotência outbound (`tests/test_automation_idempotency.py`).
- Novo teste de anti-replay de callback (`tests/test_automation_callbacks.py`).
- Mantidos testes de assinatura/retry.

### Documentação
- README atualizado com:
  - nota de idempotência outbound.
  - exemplo de callback assinado (headers + payload).
  - checklist E2E Alfred ↔ Activepieces.

---

## 5) Comandos executados (solicitados)

### 5.1 Ripgrep para localizar pontos-chave
```bash
rg -n "APIRouter\(|include_router|@router\.(get|post|patch|delete)|JWT|refresh|require_roles|tenant|publish_event|process_pending_deliveries|create_scheduler|rules_engine|normalize\(" src/api src/services src/core src/main.py
```

### 5.2 Listagem de endpoints FastAPI
```bash
python - <<'PY'
from main import app
for r in sorted(app.routes, key=lambda x: x.path):
    methods=','.join(sorted(m for m in (r.methods or []) if m not in {'HEAD','OPTIONS'}))
    if methods:
        print(f"{methods:12} {r.path}")
PY
```
(rodado em `src/`)

### 5.3 Dependências e jobs
```bash
rg -n "fastapi|pydantic|sqlalchemy|alembic|psycopg|apscheduler|python-jose|passlib|requests" requirements.txt
rg -n "add_job\(|process_pending_deliveries|check_overdue_tasks|check_stalled_leads" src/services/automation/scheduler.py src/main.py
```

---

## 6) Checklist de “funcionou” (E2E com Activepieces)
1. Subir Alfred API e DB; aplicar migrations (`alembic upgrade head`).
2. Criar usuário e obter JWT.
3. Criar destination em `/api/v1/automations/destinations` com secret e `event_types`.
4. Criar workflow no Activepieces com Webhook Trigger para URL do destination.
5. Disparar evento no Alfred (`/api/v1/webhooks/email` ou envio de mensagem outbound).
6. Confirmar recebimento no Activepieces com headers assinados.
7. No Activepieces, configurar HTTP action para callback Alfred.
8. Assinar callback com mesmo segredo e enviar para `/api/v1/automations/callbacks`.
9. Validar entidade criada/atualizada no Alfred.
10. Repetir callback com mesmo `event_id` e validar dedupe.
11. Forçar erro no destination e validar retry automático no minuto seguinte.

