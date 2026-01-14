import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getUserSupabaseClient } from "../_shared/supabase.ts";

interface Payload {
  org_id: string;
  contact_id: string;
  channel: string;
  channel_conversation_id?: string | null;
}

Deno.serve(async (req) => {
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405, headers: corsHeaders });
  }

  const supabase = getUserSupabaseClient(req);
  const { data: userData, error: userError } = await supabase.auth.getUser();
  if (userError || !userData?.user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let payload: Payload;
  try {
    payload = await req.json();
  } catch (_err) {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { org_id, contact_id, channel, channel_conversation_id } = payload;
  if (!org_id || !contact_id || !channel) {
    return new Response(JSON.stringify({ error: "org_id, contact_id, and channel are required" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { data: membership } = await supabase
    .from("memberships")
    .select("id")
    .eq("org_id", org_id)
    .eq("user_id", userData.user.id)
    .maybeSingle();

  if (!membership) {
    return new Response(JSON.stringify({ error: "Forbidden" }), {
      status: 403,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { data: contact } = await supabase
    .from("contacts")
    .select("id")
    .eq("id", contact_id)
    .eq("org_id", org_id)
    .maybeSingle();

  if (!contact) {
    return new Response(JSON.stringify({ error: "Contact not found" }), {
      status: 404,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  if (channel_conversation_id) {
    const { data: existing } = await supabase
      .from("conversations")
      .select("*")
      .eq("org_id", org_id)
      .eq("channel", channel)
      .eq("channel_conversation_id", channel_conversation_id)
      .maybeSingle();

    if (existing) {
      return new Response(JSON.stringify({ conversation: existing }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  }

  const { data: created, error: createError } = await supabase
    .from("conversations")
    .insert({
      org_id,
      contact_id,
      channel,
      channel_conversation_id: channel_conversation_id ?? null,
    })
    .select("*")
    .maybeSingle();

  if (createError || !created) {
    return new Response(JSON.stringify({ error: createError?.message ?? "Failed to create" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ conversation: created }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
