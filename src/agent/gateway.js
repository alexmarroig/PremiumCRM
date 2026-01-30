import { normalizeGatewayEvent, runAgentLoop } from './eventLoop.js';

export const handleGatewayEvent = async ({ event, teamId, authHeader }) => {
  const normalized = normalizeGatewayEvent(event);
  return runAgentLoop({ event: normalized, sessionId: normalized.sessionId, teamId, authHeader });
};
