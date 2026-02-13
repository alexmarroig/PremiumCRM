# CHECKLIST — Integração Activepieces

## Feito
- [x] Discovery completo do backend e arquitetura em `RELATORIO.md`.
- [x] Eventos outbound assinados com HMAC e anti-replay por timestamp.
- [x] Retry/backoff em `automation_deliveries` com worker APScheduler a cada 1 minuto.
- [x] Idempotência outbound com `source_event_id` em `automation_events`.
- [x] Idempotência inbound callback por `(destination_id, event_id)`.
- [x] Callback MVP com ações: `create_task`, `update_conversation_status`, `add_internal_comment`, `send_message`, `update_contact`.
- [x] Multi-tenant enforcement em callbacks (`tenant_id` x destination owner).
- [x] Auditoria de automações (`automation_event_sent`, `automation_callback_executed`) em `audit_logs`.
- [x] Secret de destination mascarado e armazenado criptografado (`secret_encrypted`).
- [x] README atualizado com variáveis env, quickstart 10 min e exemplos curl.
- [x] Testes automatizados para assinatura, anti-replay, idempotência e retry.

## Falta (próximo ciclo)
- [ ] Migrar criptografia de secret para KMS/Vault gerenciado.
- [ ] Proteção SSRF em URL de destination (deny private networks).
- [ ] Endpoint operacional para listar deliveries com filtros.
- [ ] Métricas observáveis (Prometheus / OpenTelemetry).

## Endpoints novos/atualizados
- `POST /api/v1/automations/destinations`
- `GET /api/v1/automations/destinations`
- `PATCH /api/v1/automations/destinations/{destination_id}`
- `DELETE /api/v1/automations/destinations/{destination_id}`
- `POST /api/v1/automations/callbacks`
- Alias compatível: `/v1/automations/*`

## Env vars necessárias
- `AUTOMATION_ENABLED`
- `AUTOMATION_DEFAULT_TIMEOUT_SECONDS`
- `AUTOMATION_MAX_ATTEMPTS`
- `AUTOMATION_REPLAY_WINDOW_SECONDS`
- `AUTOMATION_RATE_LIMIT_PER_MINUTE`
- `AUTOMATION_SECRET_ENCRYPTION_KEY`

## Comandos de teste
```bash
pytest -q tests/test_automation_signing.py tests/test_automation_delivery.py tests/test_automation_callbacks.py tests/test_automation_idempotency.py
```
