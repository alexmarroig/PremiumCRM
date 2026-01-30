export const baseAgents = [
  {
    id: 'alfred-sales',
    tools: [
      'sendMessage',
      'createTask',
      'getLead',
      'suggestReply',
      'createFlow',
      'predictConversion',
    ],
    triggers: ['cold-lead', 'sentiment-negative', 'whatsapp', 'inbound', 'manual'],
    stateModel: 'gpt-4o-mini',
  },
];

export const selectAgent = ({ agents, trigger, channel }) => {
  if (!agents.length) return null;
  const triggerKey = trigger || channel;
  if (!triggerKey) return agents[0];
  return (
    agents.find((agent) => agent.triggers?.includes(triggerKey)) ||
    agents.find((agent) => agent.triggers?.some((entry) => triggerKey?.includes(entry))) ||
    agents[0]
  );
};
