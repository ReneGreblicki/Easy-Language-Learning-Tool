import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
};
function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Only POST requests are supported." }, 405);
  const authorization = request.headers.get("Authorization");
  if (!authorization) return json({ error: "Sign in before managing decks." }, 401);
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!supabaseUrl || !anonKey || !serviceKey) return json({ error: "Deck maintenance is not configured correctly." }, 503);
  const userClient = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authorization } } });
  const { data: { user } } = await userClient.auth.getUser();
  if (!user) return json({ error: "Your session expired. Sign in again." }, 401);
  let body: Record<string, unknown>;
  try { body = await request.json(); } catch { return json({ error: "The maintenance request was not valid." }, 400); }
  const action = body.action;
  const deckId = body.deck_id;
  const admin = createClient(supabaseUrl, serviceKey);

  if (action === "run") {
    const now = new Date().toISOString();
    const { data: due, error } = await admin.from("decks").select("id")
      .eq("user_id", user.id).not("mobile_purge_after", "is", null).lte("mobile_purge_after", now);
    if (error) return json({ error: "Deck cleanup could not run. It will retry later." }, 503);
    for (const deck of due ?? []) {
      const { data: cards } = await admin.from("cards").select("id").eq("deck_id", deck.id).eq("user_id", user.id);
      const cardIds = (cards ?? []).map((card) => card.id);
      const paths: string[] = [];
      for (let start = 0; start < cardIds.length; start += 100) {
        const { data: audio } = await admin.from("card_audio").select("storage_path")
          .in("card_id", cardIds.slice(start, start + 100));
        paths.push(...(audio ?? []).map((item) => item.storage_path));
      }
      if (paths.length) await admin.storage.from("flashcard-audio").remove(paths);
      await admin.from("decks").delete().eq("id", deck.id).eq("user_id", user.id);
    }
    return json({ purged: due?.length ?? 0 });
  }

  if (typeof deckId !== "string") return json({ error: "Choose a valid deck." }, 400);
  if (action === "remove") {
    const removed = new Date();
    const { error } = await admin.from("decks").update({
      mobile_removed_at: removed.toISOString(),
      mobile_purge_after: new Date(removed.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString(),
    }).eq("id", deckId).eq("user_id", user.id);
    if (error) return json({ error: "The deck removal could not be scheduled. Try again." }, 503);
  } else if (action === "restore" || action === "used") {
    const values: Record<string, unknown> = { mobile_removed_at: null, mobile_purge_after: null };
    if (action === "used") values.last_used_at = new Date().toISOString();
    const { error } = await admin.from("decks").update(values).eq("id", deckId).eq("user_id", user.id);
    if (error) return json({ error: "The deck activity could not be saved. Try again." }, 503);
  } else {
    return json({ error: "Choose a valid maintenance action." }, 400);
  }
  return json({ ok: true });
});
