import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
};
const mediaTypes = new Set(["youtube", "podcast", "series", "movie", "song"]);
const levels = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function outputText(result: Record<string, unknown>) {
  if (typeof result.output_text === "string") return result.output_text;
  for (const item of (result.output as Array<Record<string, unknown>> | undefined) ?? []) {
    for (const content of (item.content as Array<Record<string, unknown>> | undefined) ?? []) {
      if (content.type === "output_text" && typeof content.text === "string") return content.text;
    }
  }
  throw new Error("No recommendation output was returned.");
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Only POST requests are supported." }, 405);
  const authorization = request.headers.get("Authorization");
  if (!authorization) return json({ error: "Sign in before requesting recommendations." }, 401);
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  const openAiKey = Deno.env.get("OPENAI_API_KEY") ?? "";
  const model = Deno.env.get("OPENAI_MODEL") ?? "gpt-5-mini";
  if (!supabaseUrl || !anonKey || !openAiKey) return json({ error: "Recommendations are not configured yet." }, 503);
  const client = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authorization } } });
  const { data: { user } } = await client.auth.getUser();
  if (!user) return json({ error: "Your session expired. Sign in again." }, 401);
  let body: Record<string, unknown>;
  try { body = await request.json(); } catch { return json({ error: "The recommendation request was not valid." }, 400); }
  const media = body.media;
  const language = body.language;
  const genre = body.genre;
  const level = body.level;
  const duration = body.duration;
  if (typeof media !== "string" || !mediaTypes.has(media) || typeof language !== "string" || !language.trim() ||
      typeof genre !== "string" || !genre.trim() || typeof level !== "string" || !levels.has(level) ||
      (media !== "movie" && media !== "song" && typeof duration !== "string")) {
    return json({ error: "Choose a valid language, media type, genre, level, and duration." }, 400);
  }
  const durationInstruction = media === "movie" || media === "song"
    ? "Do not filter by duration."
    : `Prefer content with ${duration}.`;
  const prompt = `Find exactly three currently available ${genre} ${media} options for a ${level} learner of ${language}. ` +
    `${durationInstruction} Use web search to verify that every URL opens the specific recommended item, not a search page or generic homepage. ` +
    "Prefer legal, accessible sources. Explain in one or two sentences why each option suits this learner. " +
    "Provide a direct image URL only when a reliable public thumbnail or cover URL is available; otherwise use null.";
  const schema = {
    type: "object",
    additionalProperties: false,
    required: ["results"],
    properties: {
      results: {
        type: "array", minItems: 3, maxItems: 3,
        items: {
          type: "object", additionalProperties: false,
          required: ["title", "description", "url", "image_url"],
          properties: {
            title: { type: "string", minLength: 1 },
            description: { type: "string", minLength: 1 },
            url: { type: "string", minLength: 8 },
            image_url: { type: ["string", "null"] },
          },
        },
      },
    },
  };
  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { Authorization: `Bearer ${openAiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        tools: [{ type: "web_search" }],
        input: prompt,
        text: { format: { type: "json_schema", name: "media_recommendations", strict: true, schema } },
      }),
    });
    if (!response.ok) {
      console.error("recommendation request failed", response.status, await response.text());
      return json({ error: "Suitable media could not be found right now. Try different settings." }, 502);
    }
    const parsed = JSON.parse(outputText(await response.json()));
    if (!Array.isArray(parsed.results) || parsed.results.length !== 3) throw new Error("Expected three results");
    for (const result of parsed.results) {
      const uri = new URL(result.url);
      if (uri.protocol !== "https:" && uri.protocol !== "http:") throw new Error("Invalid result link");
    }
    return json({ results: parsed.results });
  } catch (error) {
    console.error("recommendations failed", error);
    return json({ error: "The recommendations were incomplete. Try again." }, 502);
  }
});
