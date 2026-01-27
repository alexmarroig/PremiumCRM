import { supabaseAdmin } from '../utils/supabase.js';

const publicPaths = new Set([
  '/health',
  '/api/billing/stripe-webhook',
  '/api/integrations/whatsapp-webhook',
  '/api/integrations/meta-webhook',
]);

export const authMiddleware = async (request, reply) => {
  if (publicPaths.has(request.url)) {
    return;
  }
  const authHeader = request.headers.authorization || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : null;
  if (!token) {
    reply.code(401).send({ error: 'Unauthorized' });
    return;
  }

  const { data, error } = await supabaseAdmin.auth.getUser(token);
  if (error || !data?.user) {
    reply.code(401).send({ error: 'Invalid token' });
    return;
  }

  const { data: profile, error: profileError } = await supabaseAdmin
    .from('users')
    .select('id, team_id, role')
    .eq('id', data.user.id)
    .single();

  if (profileError || !profile) {
    reply.code(403).send({ error: 'User profile not found' });
    return;
  }

  request.user = {
    id: data.user.id,
    email: data.user.email,
    teamId: profile.team_id,
    role: profile.role,
  };
};

export const requireRole = (...roles) => async (request, reply) => {
  if (!request.user) {
    reply.code(401).send({ error: 'Unauthorized' });
    return;
  }
  if (!roles.includes(request.user.role)) {
    reply.code(403).send({ error: 'Insufficient role' });
  }
};
