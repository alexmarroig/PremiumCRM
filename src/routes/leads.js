import validator from 'validator';

import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';

export default async function leadsRoutes(fastify) {
  fastify.get('/api/leads/:id/full', async (request) => {
    const { id } = request.params;
    const { data: lead, error } = await supabaseAdmin.from('leads').select('*').eq('id', id).single();
    if (error) return { error: error.message };

    const { data: conversations } = await supabaseAdmin
      .from('conversations')
      .select('*')
      .eq('lead_id', id)
      .order('created_at', { ascending: false });

    return {
      lead,
      conversations: conversations || [],
    };
  });

  fastify.post('/api/leads/:id/custom-field', async (request) => {
    const { id } = request.params;
    const { key, value } = request.body || {};
    if (!validator.isAlphanumeric(String(key || ''), 'pt-BR', { ignore: '_-' })) {
      return { error: 'Invalid key' };
    }
    const { data: lead, error } = await supabaseAdmin.from('leads').select('custom_fields').eq('id', id).single();
    if (error) return { error: error.message };

    const updatedFields = { ...(lead.custom_fields || {}), [key]: value };
    const { error: updateError } = await supabaseAdmin
      .from('leads')
      .update({ custom_fields: updatedFields, updated_at: new Date().toISOString() })
      .eq('id', id);
    if (updateError) return { error: updateError.message };
    await auditLogger(request);
    return { status: 'ok', custom_fields: updatedFields };
  });

  fastify.delete('/api/leads/:id/anonymize', async (request) => {
    const { id } = request.params;
    const { error } = await supabaseAdmin
      .from('leads')
      .update({ name: null, phone: null, email: null, custom_fields: {}, updated_at: new Date().toISOString() })
      .eq('id', id);
    if (error) return { error: error.message };
    await auditLogger(request);
    return { status: 'anonymized' };
  });
}
