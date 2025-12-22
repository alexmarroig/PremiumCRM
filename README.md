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

## Visão geral do CRM Alfred
- **Autenticação e multi-tenant**: registro/login com tokens JWT de acesso/refresh; todas as consultas usam `user_id` para isolar dados.
- **Inbox unificada**: `/conversations` lista conversas com contato, canal, unread badge, sentimento/urgência derivado do último inbound e snippet da última mensagem.
- **Mensagens**: envio outbound grava mensagens, atualiza `last_message_at`, emite evento `message.sent`; inbound via webhook normalizado gera `ai_classification`, eventos e notificações.
- **Contatos e negociação**: contatos têm `contact_settings` com modo de negociação, preço base/custom, VIP e tom preferido para personalizar sugestões do Alfred.
- **Tarefas e alertas**: tarefas vinculáveis a conversas, com status/priority/due_date; endpoints permitem criar, atualizar e completar; notificações de tarefas vencidas são geradas por job horário.
- **Regras e fluxos**: regras em linguagem natural compilam para JSON (stub) e podem disparar `rule_match`; fluxos armazenam decision trees que podem ser validadas/simuladas para sugerir ações.
- **IA embutida**: `MockAIProvider` detecta sentimento, urgência, sinal de negociação e se deve criar tarefa; sugere resposta, preço (faixa) e follow-up sem depender de dados visuais.
- **Notificações**: tipos `urgent_message`, `overdue_task`, `stalled_lead`, `rule_match`, todas filtráveis por `seen`.
- **Automação e eventos**: event bus registra `ai_events` e facilita acoplamento entre ingestão de mensagens, regras e notificações; scheduler diário identifica leads parados.
- **Seed demo**: `scripts/seed_demo.py` cria usuário demo, canais e dados iniciais para explorar rapidamente.

## Funcionalidades adicionais já disponíveis
- **Pesquisa no inbox e contatos**: filtros de status, canal, unread_only, busca textual e atributos de sentimento/urgência em `/conversations`; busca por nome/handle em `/contacts`.
- **Configurações de contato**: toggle de negociação, VIP e preços customizados para influenciar sugestões do Alfred.
- **Simulação de fluxos**: `/flows/{id}/simulate` aceita texto/sentimento/intent e retorna nós combinados + ações sugeridas para testes rápidos sem enviar mensagens reais.
- **Webhook-friendly**: normalizadores para WhatsApp/Instagram/Messenger/Email aceitam payloads brutos e respondem rápido com resumo normalizado.
- **Extensível por provider**: interface `AIProvider` permite plugar modelos externos (p. ex., OpenAI) sem mudar os endpoints.

## Integração com mensageiros e n8n
- **Mensageiros**: o backend recebe inbound via endpoints `/api/v1/webhooks/{channel_type}` para `whatsapp`, `instagram`, `messenger` e `email`. O envio outbound é persistido na tabela `messages` e retorna sucesso (integrações externas reais são opcionais e podem ser acopladas por webhooks ou queues).
- **n8n**: conecte n8n usando um nó HTTP Webhook que receba eventos externos e, em seguida, chame os endpoints de webhook do Alfred com o token JWT do usuário. Também é possível acionar o Alfred a partir de n8n via nós HTTP Request para criar contatos, tarefas ou disparar IA (classify-message, suggest-reply etc.).
- **Autorização**: todos os endpoints (exceto `/health` e `/auth/*`) exigem `Authorization: Bearer <access_token>`. Gere tokens via `/auth/login` e configure-os como cabeçalho em fluxos n8n.
