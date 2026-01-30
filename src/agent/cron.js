import { Queue, Worker } from 'bullmq';
import fetch from 'node-fetch';

import { createQueueConnection } from '../utils/queue.js';
import { config } from '../utils/config.js';

const connection = createQueueConnection();
const queueName = 'agent-cron';
const agentCronQueue = new Queue(queueName, { connection });

const buildAuthHeader = () => {
  if (!config.agentServiceToken) return null;
  return `Bearer ${config.agentServiceToken}`;
};

const callAgentTrigger = async (trigger) => {
  if (!config.agentServiceToken) {
    console.warn('AGENT_SERVICE_TOKEN not set; skipping agent cron trigger.');
    return;
  }
  await fetch(`${config.agentLocalBaseUrl}/api/agent/cron/${trigger}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: buildAuthHeader(),
    },
  });
};

export const startAgentCronJobs = async () => {
  await agentCronQueue.add(
    'leads-cold',
    { trigger: 'cold-lead' },
    { repeat: { every: 3600000 }, removeOnComplete: true, removeOnFail: true }
  );
  await agentCronQueue.add(
    'sentiment-negative',
    { trigger: 'sentiment-negative' },
    { repeat: { every: 300000 }, removeOnComplete: true, removeOnFail: true }
  );

  const worker = new Worker(
    queueName,
    async (job) => {
      const trigger = job.name;
      await callAgentTrigger(trigger);
    },
    { connection }
  );

  worker.on('failed', (job, error) => {
    console.error(`Agent cron job failed: ${job?.name}`, error);
  });
};
