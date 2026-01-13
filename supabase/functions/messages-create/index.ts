import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getUserSupabaseClient } from "../_shared/supabase.ts";

interface Payload {
  org_id: string;
  conversation_id: string;
  content: string;
  is_from_customer: boolean;
  channel_message_id?: string | null;
  metadata?: Record<string, unknown> | null;
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

  const { org_id, conversation_id, content, is_from_customer, channel_message_id, metadata } = payload;
  if (!org_id || !conversation_id || !content || typeof is_from_customer !== "boolean") {
    return new Response(
      JSON.stringify({ error: "org_id, conversation_id, content, and is_from_customer are required" }),
      { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
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

  const { data: conversation } = await supabase
    .from("conversations")
    .select("id, unread_count")
    .eq("id", conversation_id)
    .eq("org_id", org_id)
    .maybeSingle();

  if (!conversation) {
    return new Response(JSON.stringify({ error: "Conversation not found" }), {
      status: 404,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  if (channel_message_id) {
    const { data: existing } = await supabase
      .from("messages")
      .select("*")
      .eq("org_id", org_id)
      .eq("channel_message_id", channel_message_id)
      .maybeSingle();

    if (existing) {
      return new Response(JSON.stringify({ message: existing }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  }

  const { data: message, error: insertError } = await supabase
    .from("messages")
    .insert({
      org_id,
      conversation_id,
      content,
      is_from_customer,
      channel_message_id: channel_message_id ?? null,
      metadata: metadata ?? {},
    })
    .select("*")
    .maybeSingle();

  if (insertError || !message) {
    return new Response(JSON.stringify({ error: insertError?.message ?? "Failed to insert" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const increment = is_from_customer ? 1 : 0;
  const unreadCount = (conversation.unread_count ?? 0) + increment;

  const { error: updateError } = await supabase
    .from("conversations")
    .update({
      last_message_at: new Date().toISOString(),
      is_unanswered: is_from_customer,
      unread_count: unreadCount,
    })
    .eq("id", conversation_id)
    .eq("org_id", org_id);

  if (updateError) {
    return new Response(JSON.stringify({ error: updateError.message }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ message }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
