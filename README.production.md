# Whisper Inbox AI (Clarity CRM) - Backend Enterprise

## Overview
Backend production-ready baseado em Node.js 20 + Fastify + Supabase + OpenAI, com RBAC, LGPD, analytics e integrações.

## Setup
1. Configure `.env` a partir de `.env.example`.
2. Instale dependências: `npm install`
3. Rode migrações: `npm run migrate`
4. Inicie o servidor: `npm run dev`

## Deploy
- Vercel: `npm run deploy`
- Supabase: use o painel para RLS e Edge Functions, conforme necessário.

## Segurança
- Supabase RLS por `team_id`
- Rate limiting via `@fastify/rate-limit`
- Logs em `audit_logs`
- Endpoint LGPD: `DELETE /api/leads/:id/anonymize`

## Integrações
- WhatsApp: `POST /api/integrations/whatsapp-webhook`
- Meta (IG/Messenger): `POST /api/integrations/meta-webhook`

## Observabilidade
- Integre com Sentry através do hook de logging do Fastify.
