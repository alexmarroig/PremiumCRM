import { supabaseAdmin } from '../utils/supabase.js';
import { buildAgentTools } from './tools.js';
import { baseAgents, selectAgent } from './registry.js';
import { applyPluginsToAgent, listPlugins } from './plugins.js';

const nowIso = () => new Date().toISOString();

const normalizeEvent = (payload = {}) => ({
  channel: payload.channel || payload.integration || payload.provider || 'unknown',
  sessionId: payload.sessionId || payload.session_id || payload.conversation_id || payload.external_id,
  conversationId: payload.conversationId || payload.conversation_id,
  leadId: payload.leadId || payload.lead_id,
  trigger: payload.trigger || payload.type,
  from: payload.from || payload.sender || payload.contact,
  content: payload.content || payload.message || payload.text || '',
  attachments: payload.attachments || payload.media || [],
  timestamp: payload.timestamp || nowIso(),
  raw: payload,
});

const buildToolPlan = ({ event, agent }) => {
  const plan = [];
  if (event.leadId && agent.tools.includes('getLead')) {
    plan.push({ tool: 'getLead', input: { leadId: event.leadId } });
  }
  if (event.trigger === 'cold-lead') {
    if (agent.tools.includes('suggestReply')) {
      plan.push({ tool: 'suggestReply', input: { message: event.content || 'Lead sem resposta há 48h.' } });
    }
    if (agent.tools.includes('sendMessage')) {
      plan.push({ tool: 'sendMessage' });
    }
    if (agent.tools.includes('createTask')) {
      plan.push({
        tool: 'createTask',
        input: {
          title: 'Follow up lead frio',
          description: 'Lead sem resposta há mais de 48h.',
          priority: 'medium',
          conversation_id: event.conversationId,
        },
      });
    }
  } else if (event.trigger === 'sentiment-negative') {
    if (agent.tools.includes('suggestReply')) {
      plan.push({ tool: 'suggestReply', input: { message: event.content || 'Cliente insatisfeito.' } });
    }
    if (agent.tools.includes('sendMessage')) {
      plan.push({ tool: 'sendMessage' });
    }
  } else if (event.content && agent.tools.includes('suggestReply')) {
    plan.push({ tool: 'suggestReply', input: { message: event.content, conversationId: event.conversationId } });
    if (agent.tools.includes('sendMessage')) {
      plan.push({ tool: 'sendMessage' });
    }
  }
  if (event.leadId && agent.tools.includes('predictConversion')) {
    plan.push({ tool: 'predictConversion', input: { leadId: event.leadId } });
  }
  return plan;
};

const persistEvent = async ({ sessionId, toolCalled, input, output, success }) => {
  await supabaseAdmin.from('agent_events').insert({
    session_id: sessionId,
    tool_called: toolCalled,
    input,
    output,
    success,
    timestamp: nowIso(),
  });
};

const ensureSession = async ({ sessionId, teamId, conversationId, agentId }) => {
  if (!sessionId) {
    const { data, error } = await supabaseAdmin
      .from('agent_sessions')
      .insert({ team_id: teamId, conversation_id: conversationId, agent_id: agentId, last_event: nowIso() })
      .select('*')
      .single();
    if (error) throw new Error(error.message);
    return data;
  }
  const { data: existing, error } = await supabaseAdmin
    .from('agent_sessions')
    .select('*')
    .eq('id', sessionId)
    .single();
  if (!error && existing) return existing;

  const { data, error: insertError } = await supabaseAdmin
    .from('agent_sessions')
    .insert({ id: sessionId, team_id: teamId, conversation_id: conversationId, agent_id: agentId, last_event: nowIso() })
    .select('*')
    .single();
  if (insertError) throw new Error(insertError.message);
  return data;
};

const updateSessionState = async ({ sessionId, state, agentId }) => {
  if (!sessionId) return;
  await supabaseAdmin
    .from('agent_sessions')
    .update({ state, last_event: nowIso(), agent_id: agentId })
    .eq('id', sessionId);
};

export const runAgentLoop = async ({ event: rawEvent, sessionId, teamId, authHeader }) => {
  const event = normalizeEvent(rawEvent || {});
  const plugins = await listPlugins({ teamId });
  const agent = applyPluginsToAgent({
    agent: selectAgent({ agents: baseAgents, trigger: event.trigger, channel: event.channel }),
    plugins,
  });
  if (!agent) {
    return { status: 'no-agent', event };
  }

  const session = await ensureSession({
    sessionId: sessionId || event.sessionId,
    teamId,
    conversationId: event.conversationId,
    agentId: agent.id,
  });

  const state = session.state || {};
  const tools = buildAgentTools({ authToken: authHeader });
  const toolPlan = buildToolPlan({ event, agent });
  const results = [];

  for (const step of toolPlan) {
    const toolName = step.tool;
    const toolInput = step.input || {};
    if (toolName === 'sendMessage') {
      toolInput.conversationId = event.conversationId;
      toolInput.message = state.lastSuggestedReply || toolInput.message || 'Posso ajudar com algo?';
    }

    let output = null;
    let success = true;
    try {
      output = await tools[toolName]?.(toolInput);
      if (toolName === 'suggestReply') {
        state.lastSuggestedReply = output?.reply || output?.suggestion || output?.message;
      }
    } catch (error) {
      success = false;
      output = { error: error.message, payload: error.payload };
    }

    await persistEvent({
      sessionId: session.id,
      toolCalled: toolName,
      input: toolInput,
      output,
      success,
    });
    results.push({ tool: toolName, input: toolInput, output, success });
  }

  await updateSessionState({ sessionId: session.id, state, agentId: agent.id });

  return {
    status: 'completed',
    session_id: session.id,
    agent_id: agent.id,
    event,
    results,
  };
};

export const normalizeGatewayEvent = (payload) => normalizeEvent(payload);
