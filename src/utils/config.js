import dotenv from 'dotenv';

dotenv.config();

const required = (key) => {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required env var: ${key}`);
  }
  return value;
};

export const config = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: Number(process.env.PORT || 3000),
  agentApiBaseUrl: process.env.AGENT_API_BASE_URL || 'http://localhost:8000',
  agentLocalBaseUrl: process.env.AGENT_LOCAL_BASE_URL || `http://localhost:${process.env.PORT || 3000}`,
  agentServiceToken: process.env.AGENT_SERVICE_TOKEN || '',
  supabaseUrl: required('SUPABASE_URL'),
  supabaseServiceKey: required('SUPABASE_SERVICE_ROLE_KEY'),
  supabaseJwtSecret: required('SUPABASE_JWT_SECRET'),
  openaiApiKey: required('OPENAI_API_KEY'),
  stripeSecretKey: required('STRIPE_SECRET_KEY'),
  stripeWebhookSecret: required('STRIPE_WEBHOOK_SECRET'),
  corsOrigins: (process.env.CORS_ORIGINS || '').split(',').filter(Boolean),
};
