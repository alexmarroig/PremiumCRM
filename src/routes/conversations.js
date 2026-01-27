import { supabaseAdmin } from '../utils/supabase.js';
import { auditLogger } from '../middleware/audit.js';

const buildTimeline = ({ conversation, tasks, comments }) => {
  const timeline = [];
  const messages = conversation.messages || [];
  for (const entry of messages) {
    timeline.push({ type: 'message', ...entry });
  }
  for (const task of tasks) {
    timeline.push({ type: 'task', ...task });
  }
  for (const comment of comments) {
    timeline.push({ type: 'comment', ...comment });
  }
  return timeline.sort((a, b) => new Date(a.timestamp || a.created_at) - new Date(b.timestamp || b.created_at));
};

export default async function conversationsRoutes(fastify) {
  fastify.get('/api/teams/:teamId/conversations', async (request) => {
    const { teamId } = request.params;
    const {
      search,
      channel,
      status,
      urgency,
      score_gt: scoreGt,
      last_contact_days: lastContactDays,
    } = request.query;

    let query = supabaseAdmin
      .from('conversations')
      .select('*')
      .eq('team_id', teamId);

    if (channel) query = query.eq('channel', channel);
    if (status) query = query.eq('status', status);
    if (urgency) query = query.eq('urgency', urgency);
    if (scoreGt) query = query.gt('score', Number(scoreGt));
    if (lastContactDays) {
      const cutoff = new Date(Date.now() - Number(lastContactDays) * 86400000).toISOString();
      query = query.gte('created_at', cutoff);
    }
    if (search) query = query.ilike('external_id', `%${search}%`);

    const { data, error } = await query.order('created_at', { ascending: false });
    if (error) return { error: error.message };
    return { results: data };
  });

  fastify.get('/api/conversations/:id', async (request) => {
    const { id } = request.params;
    const { data, error } = await supabaseAdmin.from('conversations').select('*').eq('id', id).single();
    if (error) return { error: error.message };
    return data;
  });

  fastify.post('/api/conversations/:id/history', async (request) => {
    const { id } = request.params;
    const { data: conversation, error } = await supabaseAdmin
      .from('conversations')
      .select('*')
      .eq('id', id)
      .single();
    if (error) return { error: error.message };

    const { data: tasks } = await supabaseAdmin.from('tasks').select('*').eq('conversation_id', id);
    const { data: comments } = await supabaseAdmin
      .from('internal_comments')
      .select('*')
      .eq('conversation_id', id);

    const timeline = buildTimeline({ conversation, tasks: tasks || [], comments: comments || [] });
    await supabaseAdmin.from('conversations').update({ timeline }).eq('id', id);
    await auditLogger(request);
    return { conversation_id: id, timeline };
  });

  fastify.post('/api/conversations/:id/tasks', async (request) => {
    const { id } = request.params;
    const payload = request.body || {};

    if (payload.title) {
      const { error } = await supabaseAdmin.from('tasks').insert({
        conversation_id: id,
        lead_id: payload.lead_id || null,
        title: payload.title,
        description: payload.description || null,
        priority: payload.priority || 'medium',
        due_date: payload.due_date || null,
        assignee_id: payload.assignee_id || null,
        status: payload.status || 'pending',
      });
      if (error) return { error: error.message };
    }

    const { data, error } = await supabaseAdmin
      .from('tasks')
      .select('*')
      .eq('conversation_id', id)
      .order('due_date', { ascending: true });
    if (error) return { error: error.message };
    await auditLogger(request);
    return data;
  });

  fastify.post('/api/conversations/:id/internal-comment', async (request) => {
    const { id } = request.params;
    const { text, mentions = [] } = request.body || {};
    const { error } = await supabaseAdmin.from('internal_comments').insert({
      conversation_id: id,
      user_id: request.user.id,
      text,
      mentions,
    });
    if (error) return { error: error.message };
    await auditLogger(request);
    return { status: 'ok' };
  });
}
