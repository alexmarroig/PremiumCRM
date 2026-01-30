import Fastify from 'fastify';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import sensible from '@fastify/sensible';
import rawBody from 'fastify-raw-body';

import { config } from './utils/config.js';
import { authMiddleware } from './middleware/auth.js';
import conversationsRoutes from './routes/conversations.js';
import leadsRoutes from './routes/leads.js';
import aiRoutes from './routes/ai.js';
import rulesRoutes from './routes/rules.js';
import flowsRoutes from './routes/flows.js';
import analyticsRoutes from './routes/analytics.js';
import integrationsRoutes from './routes/integrations.js';
import billingRoutes from './routes/billing.js';
import agentRoutes from './routes/agent.js';
import { startAgentCronJobs } from './agent/index.js';

const app = Fastify({ logger: true });

await app.register(rawBody, { field: 'rawBody', global: false, encoding: 'utf8' });
await app.register(sensible);
await app.register(rateLimit, { max: 120, timeWindow: '1 minute' });
await app.register(cors, {
  origin: (origin, cb) => {
    if (!origin) return cb(null, true);
    if (config.corsOrigins.length === 0 || config.corsOrigins.includes(origin)) {
      return cb(null, true);
    }
    return cb(new Error('Not allowed'), false);
  },
});

app.addHook('preHandler', authMiddleware);

await app.register(conversationsRoutes);
await app.register(leadsRoutes);
await app.register(aiRoutes);
await app.register(rulesRoutes);
await app.register(flowsRoutes);
await app.register(analyticsRoutes);
await app.register(integrationsRoutes);
await app.register(billingRoutes);
await app.register(agentRoutes);

startAgentCronJobs().catch((error) => {
  app.log.error({ error }, 'Failed to start agent cron jobs');
});

app.get('/health', async () => ({ status: 'ok' }));

app.listen({ port: config.port, host: '0.0.0.0' });
