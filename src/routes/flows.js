import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';

export default async function flowsRoutes(fastify) {
  fastify.post('/api/flows', async (request) => {
    const payload = request.body || {};
    const { data, error } = await supabaseAdmin.from('flows').insert(payload).select('*').single();
    if (error) return { error: error.message };
    await auditLogger(request);
    return { flow: data };
  });

  fastify.post('/api/flows/:id/execute', async (request) => {
    const { id } = request.params;
    const { data: flow } = await supabaseAdmin.from('flows').select('executions').eq('id', id).single();
    const nextExecutions = (flow?.executions || 0) + 1;
    await supabaseAdmin.from('flows').update({ executions: nextExecutions }).eq('id', id);
    await auditLogger(request);
    return { status: 'executed', flow_id: id, executions: nextExecutions };
  });
}
