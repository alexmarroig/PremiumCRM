import { supabaseAdmin } from '../utils/supabase.js';

export const listPlugins = async ({ teamId }) => {
  if (!teamId) return [];
  const { data, error } = await supabaseAdmin
    .from('agent_plugins')
    .select('*')
    .eq('team_id', teamId)
    .eq('active', true);
  if (error) throw new Error(error.message);
  return data || [];
};

export const createPlugin = async ({ teamId, payload }) => {
  const { data, error } = await supabaseAdmin
    .from('agent_plugins')
    .insert({
      team_id: teamId,
      name: payload.name,
      niche: payload.niche,
      tools: payload.tools || [],
      prompt_template: payload.prompt_template,
      active: payload.active ?? true,
    })
    .select('*')
    .single();
  if (error) throw new Error(error.message);
  return data;
};

export const applyPluginsToAgent = ({ agent, plugins }) => {
  if (!plugins?.length) return agent;
  const pluginTools = plugins.flatMap((plugin) => plugin.tools || []);
  const promptFragments = plugins.map((plugin) => plugin.prompt_template).filter(Boolean);
  return {
    ...agent,
    tools: Array.from(new Set([...(agent.tools || []), ...pluginTools])),
    promptTemplates: promptFragments,
    plugins,
  };
};
