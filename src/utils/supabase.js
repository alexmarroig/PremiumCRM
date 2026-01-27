import { createClient } from '@supabase/supabase-js';
import { config } from './config.js';

export const supabaseAdmin = createClient(config.supabaseUrl, config.supabaseServiceKey, {
  auth: { persistSession: false },
});
