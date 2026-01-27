import { chatCompletion, transcribeAudio, textToSpeech } from '../ai/openai.js';
import { SUMMARY_PROMPT, RESPONSE_PROMPT } from '../ai/prompts.js';
import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';

const buildHistory = (messages = []) => messages.map((msg) => `${msg.role}: ${msg.content}`).join('\n');

export default async function aiRoutes(fastify) {
  fastify.post('/api/ai/summary/:conversationId', async (request) => {
    const { conversationId } = request.params;
    const { data: conversation, error } = await supabaseAdmin
      .from('conversations')
      .select('messages, score')
      .eq('id', conversationId)
      .single();
    if (error) return { error: error.message };

    const prompt = `${SUMMARY_PROMPT}\n\n${buildHistory(conversation.messages)}`;
    const summary = await chatCompletion({
      messages: [{ role: 'system', content: SUMMARY_PROMPT }, { role: 'user', content: prompt }],
    });

    await auditLogger(request);
    return { summary, suggestions: ['Criar tarefa', 'Enviar proposta', 'Marcar call'] };
  });

  fastify.post('/api/ai/response-suggest/:conversationId', async (request) => {
    const { conversationId } = request.params;
    const { empresa_tom = 'amigável', history } = request.body || {};
    const { data: conversation } = await supabaseAdmin
      .from('conversations')
      .select('messages, score')
      .eq('id', conversationId)
      .single();

    const context = history || buildHistory(conversation?.messages || []);
    const prompt = RESPONSE_PROMPT.replace('{{empresa_tom}}', empresa_tom).replace('{{history}}', context).replace('{{score}}', conversation?.score || 0);
    const reply = await chatCompletion({
      messages: [{ role: 'system', content: RESPONSE_PROMPT }, { role: 'user', content: prompt }],
    });
    await auditLogger(request);
    return { reply };
  });

  fastify.post('/api/ai/flow-from-prompt', async (request) => {
    const { prompt } = request.body || {};
    const flowPayload = {
      name: 'Fluxo AI',
      nodes: [{ type: 'trigger', config: { prompt } }],
      active: true,
    };
    const { data, error } = await supabaseAdmin.from('flows').insert(flowPayload).select('*').single();
    if (error) return { error: error.message };
    await auditLogger(request);
    return { flow: data };
  });

  fastify.post('/api/ai/voice/transcribe', async (request) => {
    const { audio_base64: audioBase64 } = request.body || {};
    const result = await transcribeAudio(audioBase64);
    await auditLogger(request);
    return { text: result.text };
  });

  fastify.post('/api/ai/voice/tts', async (request) => {
    const { text } = request.body || {};
    const audioBase64 = await textToSpeech(text);
    await auditLogger(request);
    return { audio_base64: audioBase64 };
  });

  fastify.post('/api/ai/predict-conversion/:leadId', async (request) => {
    const { leadId } = request.params;
    const { data: lead } = await supabaseAdmin.from('leads').select('sentiment_avg, ltv').eq('id', leadId).single();
    const score = Math.min(98, Math.max(10, (lead?.sentiment_avg || 0) * 50 + 50));
    await auditLogger(request);
    return { lead_id: leadId, conversion_probability: score, churn_risk: 100 - score };
  });
}
