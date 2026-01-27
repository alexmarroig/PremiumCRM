import { supabaseAdmin } from '../utils/supabase.js';
import { chatCompletion } from '../ai/openai.js';
import { SUMMARY_PROMPT } from '../ai/prompts.js';
import { webhookQueue } from '../utils/queue.js';

const detectSentiment = (text = '') => {
  const lowered = text.toLowerCase();
  if (lowered.includes('ótimo') || lowered.includes('obrigado')) return 'positive';
  if (lowered.includes('ruim') || lowered.includes('reclama')) return 'negative';
  return 'neutral';
};

const normalizeMessage = (payload) => ({
  external_id: payload.id,
  lead_id: payload.lead_id || null,
  channel: payload.channel || 'whatsapp',
  content: payload.message || '',
  timestamp: payload.timestamp || new Date().toISOString(),
});

export default async function integrationsRoutes(fastify) {
  fastify.post('/api/integrations/whatsapp-webhook', async (request) => {
    const message = normalizeMessage(request.body || {});
    const sentiment = detectSentiment(message.content);

    const { data: conversation } = await supabaseAdmin
      .from('conversations')
      .insert({
        team_id: request.user?.teamId || null,
        lead_id: message.lead_id,
        channel: 'whatsapp',
        external_id: message.external_id,
        messages: [{ role: 'user', content: message.content, timestamp: message.timestamp, sentiment }],
        urgency: 'medium',
        status: 'lead',
      })
      .select('*')
      .single();

    await webhookQueue.add('summarize', { conversation_id: conversation?.id, content: message.content });

    const summary = await chatCompletion({
      messages: [{ role: 'system', content: SUMMARY_PROMPT }, { role: 'user', content: message.content }],
    });

    return { status: 'ok', conversation_id: conversation?.id, summary };
  });

  fastify.post('/api/integrations/meta-webhook', async (request) => {
    return { status: 'ok', provider: 'meta', payload: request.body };
  });
}
