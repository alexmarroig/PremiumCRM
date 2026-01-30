import { Queue } from 'bullmq';
import IORedis from 'ioredis';

export const createQueueConnection = () =>
  new IORedis(process.env.REDIS_URL || 'redis://localhost:6379');

const connection = createQueueConnection();

export const webhookQueue = new Queue('webhook-processing', { connection });
