import { corsHeaders, handleCors } from "../_shared/cors.ts";
import { getUserSupabaseClient } from "../_shared/supabase.ts";

interface ContactInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  tags?: string[] | null;
}

interface IdentityInput {
  channel: "whatsapp" | "instagram" | "messenger" | "email";
  external_id: string;
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

  let payload: { org_id: string; contact: ContactInput; identities?: IdentityInput[] };
  try {
    payload = await req.json();
  } catch (_err) {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { org_id, contact, identities = [] } = payload;
  if (!org_id || !contact?.name) {
    return new Response(JSON.stringify({ error: "org_id and contact.name are required" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const { data: membership, error: membershipError } = await supabase
    .from("memberships")
    .select("id")
    .eq("org_id", org_id)
    .eq("user_id", userData.user.id)
    .maybeSingle();

  if (membershipError || !membership) {
    return new Response(JSON.stringify({ error: "Forbidden" }), {
      status: 403,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let contactId: string | null = null;
  for (const identity of identities) {
    const { data: identityRow } = await supabase
      .from("contact_identities")
      .select("contact_id")
      .eq("org_id", org_id)
      .eq("channel", identity.channel)
      .eq("external_id", identity.external_id)
      .maybeSingle();

    if (identityRow?.contact_id) {
      contactId = identityRow.contact_id;
      break;
    }
  }

  let contactRecord;
  if (contactId) {
    const updatePayload: Record<string, unknown> = {};
    if (contact.name) updatePayload.name = contact.name;
    if (contact.email !== undefined) updatePayload.email = contact.email;
    if (contact.phone !== undefined) updatePayload.phone = contact.phone;
    if (contact.tags !== undefined) updatePayload.tags = contact.tags;

    const { data, error } = await supabase
      .from("contacts")
      .update(updatePayload)
      .eq("id", contactId)
      .eq("org_id", org_id)
      .select("*")
      .maybeSingle();

    if (error || !data) {
      return new Response(JSON.stringify({ error: error?.message ?? "Failed to update contact" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    contactRecord = data;
  } else {
    const { data, error } = await supabase
      .from("contacts")
      .insert({
        org_id,
        name: contact.name,
        email: contact.email,
        phone: contact.phone,
        tags: contact.tags,
      })
      .select("*")
      .maybeSingle();

    if (error || !data) {
      return new Response(JSON.stringify({ error: error?.message ?? "Failed to create contact" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    contactRecord = data;
    contactId = data.id;
  }

  if (identities.length > 0 && contactId) {
    const identityRows = identities.map((identity) => ({
      org_id,
      contact_id: contactId,
      channel: identity.channel,
      external_id: identity.external_id,
    }));

    const { error: identityError } = await supabase
      .from("contact_identities")
      .insert(identityRows, { onConflict: "org_id,channel,external_id", ignoreDuplicates: true });

    if (identityError) {
      return new Response(JSON.stringify({ error: identityError.message }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  }

  const { data: identityList } = await supabase
    .from("contact_identities")
    .select("*")
    .eq("org_id", org_id)
    .eq("contact_id", contactId ?? "");

  return new Response(
    JSON.stringify({ contact: contactRecord, identities: identityList ?? [] }),
    { headers: { ...corsHeaders, "Content-Type": "application/json" } },
  );
});
