import fetch from 'node-fetch';

import { config } from '../utils/config.js';

const jsonHeaders = (token) => {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = token;
  return headers;
};

const requestJson = async ({ url, method = 'GET', body, token }) => {
  const response = await fetch(url, {
    method,
    headers: jsonHeaders(token),
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload?.error || response.statusText);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
};

export const buildAgentTools = ({ authToken }) => {
  const apiBaseUrl = config.agentApiBaseUrl;
  const token = authToken || (config.agentServiceToken ? `Bearer ${config.agentServiceToken}` : null);

  return {
    sendMessage: async ({ conversationId, message }) =>
      requestJson({
        url: `${apiBaseUrl}/api/v1/conversations/${conversationId}/messages`,
        method: 'POST',
        body: { body: message },
        token,
      }),
    createTask: async (payload) =>
      requestJson({
        url: `${apiBaseUrl}/api/v1/tasks`,
        method: 'POST',
        body: payload,
        token,
      }),
    getLead: async ({ leadId }) =>
      requestJson({
        url: `${apiBaseUrl}/api/v1/leads/${leadId}/full`,
        method: 'GET',
        token,
      }),
    suggestReply: async ({ message, conversationId }) =>
      requestJson({
        url: `${apiBaseUrl}/api/v1/ai/suggest-reply`,
        method: 'POST',
        body: { message, conversation_id: conversationId },
        token,
      }),
    createFlow: async ({ prompt }) =>
      requestJson({
        url: `${apiBaseUrl}/api/v1/ai/flow/create`,
        method: 'POST',
        body: { prompt },
        token,
      }),
    predictConversion: async ({ leadId }) =>
      requestJson({
        url: `${apiBaseUrl}/api/ai/predict-conversion/${leadId}`,
        method: 'POST',
        token,
      }),
  };
};
