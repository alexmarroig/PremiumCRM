import { supabaseAdmin } from '../utils/supabase.js';

export const auditLogger = async (request) => {
  if (!request.user) {
    return;
  }
  const payload = {
    team_id: request.user.teamId,
    user_id: request.user.id,
    action: `${request.method} ${request.url}`,
    conversation_id: request.params?.id || request.params?.conversationId || null,
    details: request.body || {},
    ip_address: request.ip,
  };
  await supabaseAdmin.from('audit_logs').insert(payload);
};
