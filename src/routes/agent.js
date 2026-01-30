import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';
import {
  baseAgents,
  createPlugin,
  handleGatewayEvent,
  runAgentLoop,
} from '../agent/index.js';

const normalizeWebhookEvent = (payload) => ({
  channel: payload.channel || 'whatsapp',
  sessionId: payload.sessionId || payload.session_id || payload.conversation_id,
  conversationId: payload.conversationId || payload.conversation_id,
  leadId: payload.leadId || payload.lead_id,
  from: payload.from || payload.sender,
  content: payload.content || payload.message || '',
  attachments: payload.attachments || [],
  timestamp: payload.timestamp,
  trigger: payload.trigger,
  raw: payload,
});

export default async function agentRoutes(fastify) {
  fastify.post('/api/agent/gateway', async (request) => {
    const event = normalizeWebhookEvent(request.body || {});
    const result = await handleGatewayEvent({
      event,
      teamId: request.user?.teamId,
      authHeader: request.headers.authorization,
    });
    await auditLogger(request);
    return result;
  });

  fastify.post('/api/agent/run', async (request) => {
    const payload = request.body || {};
    const result = await runAgentLoop({
      event: payload.event || payload.trigger || payload,
      sessionId: payload.sessionId,
      teamId: request.user?.teamId,
      authHeader: request.headers.authorization,
    });
    await auditLogger(request);
    return result;
  });

  fastify.get('/api/agent/agents', async (request) => {
    const { data: plugins } = await supabaseAdmin
      .from('agent_plugins')
      .select('*')
      .eq('team_id', request.user?.teamId || null)
      .eq('active', true);

    const response = baseAgents.map((agent) => ({
      ...agent,
      plugin_count: plugins?.length || 0,
    }));
    await auditLogger(request);
    return { agents: response };
  });

  fastify.post('/api/agent/plugins', async (request) => {
    const payload = request.body || {};
    const plugin = await createPlugin({ teamId: request.user?.teamId, payload });
    await auditLogger(request);
    return { plugin };
  });

  fastify.post('/api/agent/cron/:trigger', async (request) => {
    const { trigger } = request.params;
    let events = [];
    if (trigger === 'leads-cold') {
      const cutoff = new Date(Date.now() - 48 * 3600 * 1000).toISOString();
      const { data } = await supabaseAdmin
        .from('conversations')
        .select('id, lead_id')
        .eq('team_id', request.user?.teamId || null)
        .lt('created_at', cutoff)
        .eq('status', 'lead');
      events = (data || []).map((row) => ({
        trigger: 'cold-lead',
        conversationId: row.id,
        leadId: row.lead_id,
        content: 'Lead sem resposta há 48h.',
      }));
    }
    if (trigger === 'sentiment-negative') {
      const { data } = await supabaseAdmin
        .from('conversations')
        .select('id, lead_id, score')
        .eq('team_id', request.user?.teamId || null)
        .lt('score', 40);
      events = events.concat(
        (data || []).map((row) => ({
          trigger: 'sentiment-negative',
          conversationId: row.id,
          leadId: row.lead_id,
          content: 'Sinal de sentimento negativo detectado.',
        }))
      );
    }

    const results = [];
    for (const event of events) {
      const result = await runAgentLoop({
        event,
        teamId: request.user?.teamId,
        authHeader: request.headers.authorization,
      });
      results.push(result);
    }

    await auditLogger(request);
    return { trigger, handled: results.length, results };
  });
}
