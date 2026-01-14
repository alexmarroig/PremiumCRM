import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getUserSupabaseClient } from "../_shared/supabase.ts";

interface Payload {
  org_id: string;
  conversation_id: string;
  goal?: "sell" | "schedule" | "support";
  constraints?: Record<string, unknown>;
}

const openAiKey = Deno.env.get("OPENAI_API_KEY");
const openAiModel = Deno.env.get("OPENAI_MODEL") ?? "gpt-4o-mini";

Deno.serve(async (req) => {
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405, headers: corsHeaders });
  }

  if (!openAiKey) {
    return new Response(JSON.stringify({ error: "OpenAI key not configured" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
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

  const { org_id, conversation_id, goal, constraints } = payload;
  if (!org_id || !conversation_id) {
    return new Response(JSON.stringify({ error: "org_id and conversation_id are required" }), {
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

  const { data: conversation } = await supabase
    .from("conversations")
    .select("id, contact_id")
    .eq("id", conversation_id)
    .eq("org_id", org_id)
    .maybeSingle();

  if (!conversation) {
    return new Response(JSON.stringify({ error: "Conversation not found" }), {
      status: 404,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { data: contact } = await supabase
    .from("contacts")
    .select("name, email, phone, tags")
    .eq("id", conversation.contact_id)
    .eq("org_id", org_id)
    .maybeSingle();

  const { data: messages } = await supabase
    .from("messages")
    .select("content, is_from_customer, created_at")
    .eq("conversation_id", conversation_id)
    .eq("org_id", org_id)
    .order("created_at", { ascending: false })
    .limit(20);

  const { data: deal } = await supabase
    .from("deals")
    .select("title, value, status")
    .eq("org_id", org_id)
    .eq("contact_id", conversation.contact_id)
    .eq("status", "open")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const prompt = `Você é Alfred, assistente de CRM. Gere uma sugestão de resposta curta em português. Não envie mensagens automaticamente. Responda apenas JSON com o campo draft_reply.`;

  const openAiResponse = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${openAiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: openAiModel,
      messages: [
        { role: "system", content: prompt },
        {
          role: "user",
          content: JSON.stringify({
            goal: goal ?? "support",
            constraints: constraints ?? {},
            contact,
            deal,
            messages: (messages ?? []).reverse().map((message) => ({
              from: message.is_from_customer ? "cliente" : "time",
              text: message.content,
            })),
          }),
        },
      ],
      response_format: { type: "json_object" },
      temperature: 0.4,
    }),
  });

  if (!openAiResponse.ok) {
    const errorText = await openAiResponse.text();
    return new Response(JSON.stringify({ error: errorText }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const openAiPayload = await openAiResponse.json();
  const content = openAiPayload.choices?.[0]?.message?.content ?? "{}";
  let parsed;
  try {
    parsed = JSON.parse(content);
  } catch (_err) {
    return new Response(JSON.stringify({ error: "Failed to parse OpenAI response" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const draftReply = parsed.draft_reply ?? "";
  if (!draftReply) {
    return new Response(JSON.stringify({ error: "Draft reply not generated" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { error: insertError } = await supabase
    .from("alfred_suggestions")
    .insert({
      org_id,
      conversation_id,
      type: "draft_reply",
      content: draftReply,
    });

  if (insertError) {
    return new Response(JSON.stringify({ error: insertError.message }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ draft_reply: draftReply }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
