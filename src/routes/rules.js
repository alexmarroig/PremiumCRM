import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';

export default async function rulesRoutes(fastify) {
  fastify.post('/api/rules', async (request) => {
    const payload = request.body || {};
    const { data, error } = await supabaseAdmin.from('rules').insert(payload).select('*').single();
    if (error) return { error: error.message };
    await auditLogger(request);
    return { rule: data };
  });
}
