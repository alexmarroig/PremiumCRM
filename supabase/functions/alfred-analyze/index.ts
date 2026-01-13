import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getUserSupabaseClient } from "../_shared/supabase.ts";

interface Payload {
  org_id: string;
  conversation_id: string;
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

  const { org_id, conversation_id } = payload;
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
    .select("id")
    .eq("id", conversation_id)
    .eq("org_id", org_id)
    .maybeSingle();

  if (!conversation) {
    return new Response(JSON.stringify({ error: "Conversation not found" }), {
      status: 404,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { data: messages } = await supabase
    .from("messages")
    .select("content, is_from_customer, created_at")
    .eq("conversation_id", conversation_id)
    .eq("org_id", org_id)
    .order("created_at", { ascending: false })
    .limit(30);

  const orderedMessages = (messages ?? []).reverse();

  const prompt = `Você é Alfred, um assistente de CRM. Analise a conversa e retorne apenas JSON válido com os campos sentiment (calm|neutral|anxious|irritated|frustrated), urgency (low|medium|high) e summary (2-5 linhas em português).`;

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
          content: JSON.stringify(
            orderedMessages.map((message) => ({
              from: message.is_from_customer ? "cliente" : "time",
              text: message.content,
              at: message.created_at,
            })),
          ),
        },
      ],
      response_format: { type: "json_object" },
      temperature: 0.2,
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

  const sentiment = parsed.sentiment ?? "neutral";
  const urgency = parsed.urgency ?? "medium";
  const summary = parsed.summary ?? null;

  const { error: updateError } = await supabase
    .from("conversations")
    .update({ sentiment, urgency, summary })
    .eq("id", conversation_id)
    .eq("org_id", org_id);

  if (updateError) {
    return new Response(JSON.stringify({ error: updateError.message }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ sentiment, urgency, summary }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
