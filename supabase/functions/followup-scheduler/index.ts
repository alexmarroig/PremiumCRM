import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getServiceSupabaseClient } from "../_shared/supabase.ts";

const cronSecret = Deno.env.get("CRON_SECRET");
const followupHours = Number(Deno.env.get("FOLLOWUP_HOURS") ?? 48);

Deno.serve(async (req) => {
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405, headers: corsHeaders });
  }

  if (cronSecret) {
    const authHeader = req.headers.get("Authorization") ?? "";
    if (authHeader !== `Bearer ${cronSecret}`) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  }

  const supabase = getServiceSupabaseClient();
  const cutoff = new Date(Date.now() - followupHours * 60 * 60 * 1000).toISOString();

  const { data: conversations, error } = await supabase
    .from("conversations")
    .select("id, org_id, contact_id, last_message_at")
    .or(`is_unanswered.eq.true,last_message_at.lt.${cutoff}`)
    .limit(200);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const dueDate = new Date().toISOString().split("T")[0] + "T00:00:00Z";
  const tasksToCreate = (conversations ?? []).map((conversation) => ({
    org_id: conversation.org_id,
    conversation_id: conversation.id,
    contact_id: conversation.contact_id,
    title: "Follow up",
    description: "Follow up overdue conversation.",
    due_date: dueDate,
    priority: "medium",
  }));

  if (tasksToCreate.length > 0) {
    const { error: taskError } = await supabase
      .from("tasks")
      .insert(tasksToCreate, { ignoreDuplicates: true });

    if (taskError) {
      return new Response(JSON.stringify({ error: taskError.message }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  }

  return new Response(JSON.stringify({ created: tasksToCreate.length }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
