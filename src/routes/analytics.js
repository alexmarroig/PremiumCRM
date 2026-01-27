import { supabaseAdmin } from '../utils/supabase.js';

export default async function analyticsRoutes(fastify) {
  fastify.get('/api/analytics/:teamId', async (request) => {
    const { teamId } = request.params;
    const { data, error } = await supabaseAdmin
      .from('analytics_daily')
      .select('*')
      .eq('team_id', teamId)
      .order('date', { ascending: false });
    if (error) return { error: error.message };
    return { team_id: teamId, analytics: data };
  });

  fastify.get('/api/agent-performance/:teamId', async (request) => {
    const { teamId } = request.params;
    const { data, error } = await supabaseAdmin
      .from('agent_performance')
      .select('*')
      .eq('team_id', teamId)
      .order('date', { ascending: false });
    if (error) return { error: error.message };
    return { team_id: teamId, performance: data };
  });
}
