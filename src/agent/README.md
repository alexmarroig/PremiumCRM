# Whisper Agent Backend (Moltbot-inspired)

> AGPL-3.0 compliant — attribution: "Inspired by Moltbot (AGPL-3.0)".

Whisper Agent é um fork conceitual do Moltbot adaptado para CRM WhatsApp/Vendas. Ele adiciona uma camada de agentes que recebem eventos normalizados, escolhem um agente e executam ferramentas sobre os endpoints já existentes do CRM.

## Arquitetura

### 1) Gateway Layer (`/api/agent/gateway`)
- Recebe webhooks (`/api/integrations/whatsapp-webhook`, etc.).
- Normaliza o payload: `{channel, sessionId, from, content, attachments, timestamp}`.
- Encaminha para o Agent Registry.

### 2) Agent Registry (`/api/agent/agents`)
- Lista agents configurados, ex:
  ```json
  [{"id":"alfred-sales","tools":["sendMessage","createTask"],"triggers":["cold-lead"],"stateModel":"gpt-4o-mini"}]
  ```
- **Tools** são wrappers para endpoints existentes:
  - `sendMessage`: `POST /api/v1/conversations/:id/messages`
  - `createTask`: `POST /api/v1/tasks`
  - `getLead`: `GET /api/v1/leads/:id/full`
  - `suggestReply`: `POST /api/v1/ai/suggest-reply`
  - `createFlow`: `POST /api/v1/ai/flow/create`
  - `predictConversion`: `POST /api/ai/predict-conversion/:leadId`

### 3) Event Loop (`/api/agent/run`)
- Recebe evento → escolhe agent → chama tools em loop até final.
- Estado persiste em `agent_sessions` (sessionId, agentId, state JSONB, last_event).

### 4) Cron Triggers (BullMQ)
- `leads-cold`: a cada 1h, busca leads sem resposta > 48h → trigger `alfred-sales`.
- `sentiment-negative`: a cada 5min, monitora score baixo → auto-reply.

### 5) Plugins/Skills (`/api/agent/plugins`)
- Tabela: `{id, name, niche: 'ecommerce', tools: [...], promptTemplate}`.
- Plugins estendem tools + prompt do agente.

## Endpoints novos
- `POST /api/agent/run` — `{event, sessionId}` → executa agent loop.
- `GET /api/agent/agents` — lista configs.
- `POST /api/agent/plugins` — instala skill.
- `POST /api/agent/cron/:trigger` — manual trigger.
- `POST /api/agent/gateway` — normalização + roteamento.

## Migrations
Incluídas em `supabase/migrations/enterprise/002_whisper_agent.sql`:
- `agent_sessions`
- `agent_events`
- `agent_plugins`

## Variáveis de ambiente
- `AGENT_API_BASE_URL` (default: `http://localhost:8000`) — base para endpoints FastAPI.
- `AGENT_LOCAL_BASE_URL` (default: `http://localhost:3000`) — base local Fastify.
- `AGENT_SERVICE_TOKEN` — token Bearer para chamadas internas.

## Exemplo de cron (BullMQ)
```js
setInterval(() => {
  // Query leads frios
  // Trigger /api/agent/run {trigger: 'cold-lead'}
}, 3600000);
```
