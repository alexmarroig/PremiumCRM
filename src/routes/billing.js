import Stripe from 'stripe';
import { config } from '../utils/config.js';
import { supabaseAdmin } from '../utils/supabase.js';

const stripe = new Stripe(config.stripeSecretKey, { apiVersion: '2024-06-20' });

export default async function billingRoutes(fastify) {
  fastify.get('/api/billing/usage', async (request) => {
    const { teamId } = request.user;
    const { data: analytics } = await supabaseAdmin
      .from('analytics_daily')
      .select('total_messages')
      .eq('team_id', teamId);
    const totalMessages = (analytics || []).reduce((sum, entry) => sum + (entry.total_messages || 0), 0);
    return { team_id: teamId, total_messages: totalMessages };
  });

  fastify.post('/api/billing/stripe-webhook', { config: { rawBody: true } }, async (request, reply) => {
    const signature = request.headers['stripe-signature'];
    let event;
    try {
      event = stripe.webhooks.constructEvent(request.rawBody, signature, config.stripeWebhookSecret);
    } catch (err) {
      reply.code(400).send({ error: `Webhook Error: ${err.message}` });
      return;
    }

    if (event.type === 'customer.subscription.updated') {
      const subscription = event.data.object;
      await supabaseAdmin
        .from('teams')
        .update({ plan: subscription.items.data[0]?.price?.metadata?.plan || 'starter' })
        .eq('stripe_customer_id', subscription.customer);
    }

    reply.send({ received: true });
  });
}
