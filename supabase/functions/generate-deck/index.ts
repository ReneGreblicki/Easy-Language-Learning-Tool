import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
};

const allowedLanguages = new Set([
  "en-US",
  "es-ES",
  "de-DE",
  "pt-PT",
  "fr-FR",
  "it-IT",
  "th-Thai-TH",
  "th-Latn-TH",
]);
const allowedLevels = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const maxWords = { A1: 5, A2: 8, B1: 11, B2: 14, C1: 17, C2: 20 };

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function validTask(task: Record<string, unknown>) {
  return Number.isInteger(task.row_number) &&
    typeof task.lemma === "string" &&
    task.lemma.trim().length > 0 &&
    typeof task.part_of_speech === "string" &&
    Array.isArray(task.known_forms) &&
    typeof task.preferred_surface_form === "string" &&
    typeof task.baseline_translation === "string" &&
    typeof task.cefr === "string" &&
    allowedLevels.has(task.cefr) &&
    (task.sentence_kind === "question" || task.sentence_kind === "statement") &&
    typeof task.grammatical_person === "string" &&
    Number.isInteger(task.form_index) &&
    Number(task.form_index) >= 0 &&
    Number(task.form_index) <= 4;
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Only POST requests are supported." }, 405);

  const authorization = request.headers.get("Authorization");
  if (!authorization) return json({ error: "Sign in before generating a deck." }, 401);

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  const openAiKey = Deno.env.get("OPENAI_API_KEY") ?? "";
  const model = Deno.env.get("OPENAI_MODEL") ?? "gpt-5-mini";
  if (!supabaseUrl || !anonKey || !serviceKey) {
    return json({ error: "The generation service is not configured correctly." }, 503);
  }
  if (!openAiKey) {
    return json({ error: "Deck generation is not enabled yet. Contact the app administrator." }, 503);
  }

  const userClient = createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authorization } },
  });
  const { data: { user }, error: userError } = await userClient.auth.getUser();
  if (userError || !user) return json({ error: "Your session expired. Sign in again." }, 401);

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: "The generation request was not valid." }, 400);
  }
  const learningCode = body.learning_language_code;
  const translationCode = body.translation_language_code;
  const learning = body.learning_language;
  const translation = body.translation_language;
  const tasks = body.tasks;
  if (
    typeof learningCode !== "string" ||
    typeof translationCode !== "string" ||
    !allowedLanguages.has(learningCode) ||
    !allowedLanguages.has(translationCode) ||
    learningCode === translationCode ||
    typeof learning !== "string" ||
    typeof translation !== "string" ||
    !Array.isArray(tasks) ||
    tasks.length < 1 ||
    tasks.length > 20 ||
    !tasks.every((task) => task && typeof task === "object" && validTask(task))
  ) {
    return json({ error: "Choose valid languages and generation settings." }, 400);
  }

  const admin = createClient(supabaseUrl, serviceKey);
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const { data: recent, error: usageError } = await admin
    .from("mobile_generation_usage")
    .select("requested_rows")
    .eq("user_id", user.id)
    .gte("created_at", since);
  if (usageError) {
    console.error("usage lookup failed", usageError);
    return json({ error: "The generation service is temporarily unavailable." }, 503);
  }
  const used = (recent ?? []).reduce(
    (sum, row) => sum + Number(row.requested_rows ?? 0),
    0,
  );
  if (used + tasks.length > 5000) {
    return json({
      error: "The 5,000-row mobile generation limit for the last 24 hours has been reached.",
    }, 429);
  }

  const requestId = crypto.randomUUID();
  const { error: insertError } = await admin.from("mobile_generation_usage").insert({
    id: requestId,
    user_id: user.id,
    requested_rows: tasks.length,
    status: "started",
  });
  if (insertError) {
    console.error("usage insert failed", insertError);
    return json({ error: "The generation service is temporarily unavailable." }, 503);
  }

  const scriptInstruction = learningCode === "th-Thai-TH"
    ? " Write Thai learning-language fields only in standard Thai script."
    : learningCode === "th-Latn-TH"
    ? " Write Thai learning-language fields only in tone-marked Paiboon romanization; do not use Thai script."
    : "";
  const prompt =
    `Create formal, standard language-learning examples. The learning language is ${learning}; translate accurately and directly into ${translation}.${scriptInstruction} ` +
    "Use every assigned word naturally and preserve its assigned part of speech. " +
    "Use the preferred surface form when provided. Extra-form rows must use a distinct valid grammatical form, or a clearly different context when the word is invariant. " +
    "Every sentence must stand alone, obey the requested question or statement type, reflect the assigned grammatical person, avoid slang, and stay within the CEFR maximum word count. " +
    "Return only the required JSON. TASKS=" +
    JSON.stringify(tasks.map((task) => ({
      ...task,
      maximum_words: maxWords[task.cefr as keyof typeof maxWords],
    })));

  const schema = {
    type: "object",
    additionalProperties: false,
    required: ["rows"],
    properties: {
      rows: {
        type: "array",
        minItems: tasks.length,
        maxItems: tasks.length,
        items: {
          type: "object",
          additionalProperties: false,
          required: [
            "row_number",
            "foreign_word",
            "word_translation",
            "foreign_sentence",
            "sentence_translation",
          ],
          properties: {
            row_number: { type: "integer" },
            foreign_word: { type: "string", minLength: 1 },
            word_translation: { type: "string", minLength: 1 },
            foreign_sentence: { type: "string", minLength: 1 },
            sentence_translation: { type: "string", minLength: 1 },
          },
        },
      },
    },
  };

  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${openAiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        input: prompt,
        text: {
          format: {
            type: "json_schema",
            name: "language_rows",
            strict: true,
            schema,
          },
        },
      }),
    });
    if (!response.ok) {
      console.error("OpenAI request failed", response.status, await response.text());
      await admin.from("mobile_generation_usage").update({ status: "failed" }).eq("id", requestId);
      return json({ error: "The language service could not generate this batch. Try again." }, 502);
    }
    const result = await response.json();
    let outputText = result.output_text;
    if (!outputText) {
      for (const item of result.output ?? []) {
        for (const content of item.content ?? []) {
          if (content.type === "output_text") outputText = content.text;
        }
      }
    }
    if (typeof outputText !== "string") throw new Error("Missing output text");
    const parsed = JSON.parse(outputText);
    if (!Array.isArray(parsed.rows) || parsed.rows.length !== tasks.length) {
      throw new Error("Incomplete row array");
    }
    const expected = new Set(tasks.map((task) => task.row_number));
    for (const row of parsed.rows) {
      if (!expected.has(row.row_number)) throw new Error("Unexpected row number");
      for (const field of [
        "foreign_word",
        "word_translation",
        "foreign_sentence",
        "sentence_translation",
      ]) {
        if (typeof row[field] !== "string" || !row[field].trim()) {
          throw new Error(`Missing ${field}`);
        }
      }
    }
    await admin.from("mobile_generation_usage").update({
      status: "completed",
      completed_at: new Date().toISOString(),
    }).eq("id", requestId);
    return json({ rows: parsed.rows });
  } catch (error) {
    console.error("generation failed", error);
    await admin.from("mobile_generation_usage").update({ status: "failed" }).eq("id", requestId);
    return json({ error: "The generated data was incomplete. Try this batch again." }, 502);
  }
});
