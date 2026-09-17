import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
};
const allowedLanguages = new Set([
  "en-US", "es-ES", "de-DE", "pt-PT", "fr-FR", "it-IT", "th-Thai-TH", "th-Latn-TH",
]);
const allowedLevels = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const maxWords = { A1: 5, A2: 8, B1: 11, B2: 14, C1: 17, C2: 20 };
const batchSize = 24;
const parallelBatches = 6;

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function validTask(task: Record<string, unknown>) {
  return Number.isInteger(task.row_number) &&
    typeof task.lemma === "string" && task.lemma.trim().length > 0 &&
    typeof task.part_of_speech === "string" && Array.isArray(task.known_forms) &&
    typeof task.preferred_surface_form === "string" &&
    typeof task.baseline_translation === "string" &&
    typeof task.cefr === "string" && allowedLevels.has(task.cefr) &&
    (task.sentence_kind === "question" || task.sentence_kind === "statement") &&
    typeof task.grammatical_person === "string" &&
    Number.isInteger(task.form_index) && Number(task.form_index) >= 0 && Number(task.form_index) <= 4;
}

function outputText(result: Record<string, unknown>) {
  if (typeof result.output_text === "string") return result.output_text;
  for (const item of (result.output as Array<Record<string, unknown>> | undefined) ?? []) {
    for (const content of (item.content as Array<Record<string, unknown>> | undefined) ?? []) {
      if (content.type === "output_text" && typeof content.text === "string") return content.text;
    }
  }
  throw new Error("The language service returned no text.");
}

type GenerationResult = {
  rows: Array<Record<string, unknown>>;
  model: string;
  attempts: number;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  usedFallback: boolean;
  validationErrors: string[];
};

class GenerationFailure extends Error {
  attempts: number;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
  validationErrors: string[];

  constructor(
    message: string,
    attempts: number,
    latencyMs: number,
    inputTokens: number,
    outputTokens: number,
    validationErrors: string[],
  ) {
    super(message);
    this.attempts = attempts;
    this.latencyMs = latencyMs;
    this.inputTokens = inputTokens;
    this.outputTokens = outputTokens;
    this.validationErrors = validationErrors;
  }
}

function normalized(value: unknown) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase()
    .replace(/[\p{P}\p{S}]+/gu, " ").replace(/\s+/g, " ").trim();
}

function validateGeneratedRows(
  job: Record<string, unknown>,
  tasks: Array<Record<string, unknown>>,
  rows: Array<Record<string, unknown>>,
) {
  const errors: string[] = [];
  const tasksByRow = new Map(tasks.map((task) => [Number(task.row_number), task]));
  const seenRows = new Set<number>();
  const seenSentences = new Set<string>();
  const learningCode = String(job.source_language_code);

  for (const row of rows) {
    const rowNumber = Number(row.row_number);
    const task = tasksByRow.get(rowNumber);
    if (!task) {
      errors.push(`row ${rowNumber}: unexpected row number`);
      continue;
    }
    if (seenRows.has(rowNumber)) errors.push(`row ${rowNumber}: duplicate row number`);
    seenRows.add(rowNumber);

    const word = String(row.foreign_word ?? "").trim();
    const sentence = String(row.foreign_sentence ?? "").trim();
    const wordTranslation = String(row.word_translation ?? "").trim();
    const sentenceTranslation = String(row.sentence_translation ?? "").trim();
    if (!word || !sentence || !wordTranslation || !sentenceTranslation) {
      errors.push(`row ${rowNumber}: one or more required values are empty`);
      continue;
    }

    const normalizedWord = normalized(word);
    const normalizedSentence = normalized(sentence);
    if (normalizedWord && !normalizedSentence.includes(normalizedWord)) {
      errors.push(`row ${rowNumber}: generated word is not used in the sentence`);
    }
    if (seenSentences.has(normalizedSentence)) {
      errors.push(`row ${rowNumber}: duplicate learning-language sentence`);
    }
    seenSentences.add(normalizedSentence);

    if (task.sentence_kind === "question" && !/[?？]\s*$/.test(sentence)) {
      errors.push(`row ${rowNumber}: requested question is not punctuated as a question`);
    }
    if (learningCode === "th-Thai-TH" && !/[\u0E00-\u0E7F]/u.test(word + sentence)) {
      errors.push(`row ${rowNumber}: Thai-script output is missing Thai characters`);
    }
    if (learningCode === "th-Latn-TH" && /[\u0E00-\u0E7F]/u.test(word + sentence)) {
      errors.push(`row ${rowNumber}: romanized Thai output contains Thai script`);
    }
    if (!learningCode.startsWith("th-")) {
      const maximum = maxWords[String(task.cefr) as keyof typeof maxWords];
      const wordCount = sentence.split(/\s+/u).filter(Boolean).length;
      if (maximum && wordCount > maximum) {
        errors.push(`row ${rowNumber}: sentence exceeds the CEFR word limit`);
      }
    }
  }

  for (const task of tasks) {
    if (!seenRows.has(Number(task.row_number))) {
      errors.push(`row ${task.row_number}: expected row is missing`);
    }
  }
  return errors;
}

async function generateBatch(
  openAiKey: string,
  model: string,
  job: Record<string, unknown>,
  tasks: Array<Record<string, unknown>>,
) {
  const learningCode = String(job.source_language_code);
  const scriptInstruction = learningCode === "th-Thai-TH"
    ? " Write Thai learning-language fields only in standard Thai script."
    : learningCode === "th-Latn-TH"
    ? " Write Thai learning-language fields only in tone-marked Paiboon romanization; do not use Thai script."
    : "";
  const prompt =
    `Create formal, standard language-learning examples. The learning language is ${job.source_language}; ` +
    `translate accurately and directly into ${job.translation_language}.${scriptInstruction} ` +
    "Use every assigned word naturally and preserve its assigned part of speech. Use the preferred surface form when provided. " +
    "Extra-form rows must use a distinct valid grammatical form, or a clearly different context when the word is invariant. " +
    "Every sentence must stand alone, obey the requested question or statement type, reflect the assigned grammatical person, " +
    "avoid slang, and stay within the CEFR maximum word count. Return only the required JSON. TASKS=" +
    JSON.stringify(tasks.map((task) => ({
      ...task,
      maximum_words: maxWords[String(task.cefr) as keyof typeof maxWords],
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
          required: ["row_number", "foreign_word", "word_translation", "foreign_sentence", "sentence_translation"],
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

  let lastError: unknown;
  let attempts = 0;
  let latencyMs = 0;
  let inputTokens = 0;
  let outputTokens = 0;
  const validationErrors: string[] = [];

  for (let attempt = 0; attempt < 2; attempt++) {
    attempts += 1;
    const started = performance.now();
    let requestLatencyRecorded = false;
    try {
      const requestBody: Record<string, unknown> = {
        model,
        input: prompt,
        text: { format: { type: "json_schema", name: "language_rows", strict: true, schema } },
      };
      if (model.startsWith("gpt-5.4") || model.startsWith("gpt-5.6")) {
        requestBody.reasoning = { effort: "none" };
      }
      const response = await fetch("https://api.openai.com/v1/responses", {
        method: "POST",
        headers: { Authorization: `Bearer ${openAiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      latencyMs += Math.round(performance.now() - started);
      requestLatencyRecorded = true;
      if (!response.ok) throw new Error(`Language service returned ${response.status}: ${await response.text()}`);
      const result = await response.json() as Record<string, unknown>;
      const usage = result.usage as Record<string, unknown> | undefined;
      inputTokens += Number(usage?.input_tokens ?? 0);
      outputTokens += Number(usage?.output_tokens ?? 0);
      const parsed = JSON.parse(outputText(result));
      if (!Array.isArray(parsed.rows) || parsed.rows.length !== tasks.length) {
        throw new Error("Incomplete row array");
      }
      const errors = validateGeneratedRows(job, tasks, parsed.rows);
      if (errors.length) {
        validationErrors.push(...errors);
        throw new Error(`Quality validation failed: ${errors.slice(0, 5).join("; ")}`);
      }
      return {
        rows: parsed.rows as Array<Record<string, unknown>>,
        model,
        attempts,
        latencyMs,
        inputTokens,
        outputTokens,
        usedFallback: false,
        validationErrors,
      } satisfies GenerationResult;
    } catch (error) {
      if (!requestLatencyRecorded) latencyMs += Math.round(performance.now() - started);
      lastError = error;
      if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  const message = lastError instanceof Error ? lastError.message : String(lastError);
  throw new GenerationFailure(message, attempts, latencyMs, inputTokens, outputTokens, validationErrors);
}

async function generateWithFallback(
  openAiKey: string,
  primaryModel: string,
  fallbackModel: string,
  job: Record<string, unknown>,
  tasks: Array<Record<string, unknown>>,
) {
  try {
    return await generateBatch(openAiKey, primaryModel, job, tasks);
  } catch (primaryError) {
    const first = primaryError instanceof GenerationFailure
      ? primaryError
      : new GenerationFailure(String(primaryError), 1, 0, 0, 0, []);
    const fallback = await generateBatch(openAiKey, fallbackModel, job, tasks);
    return {
      ...fallback,
      attempts: first.attempts + fallback.attempts,
      latencyMs: first.latencyMs + fallback.latencyMs,
      inputTokens: first.inputTokens + fallback.inputTokens,
      outputTokens: first.outputTokens + fallback.outputTokens,
      usedFallback: true,
      validationErrors: [first.message, ...first.validationErrors],
    } satisfies GenerationResult;
  }
}

async function finalizeJob(admin: ReturnType<typeof createClient>, job: Record<string, unknown>) {
  const jobId = String(job.id);
  const { data: batches, error: batchError } = await admin
    .from("mobile_generation_batches")
    .select("batch_index,rows,status,used_fallback,input_tokens,output_tokens,latency_ms")
    .eq("job_id", jobId)
    .order("batch_index");
  if (batchError) throw batchError;
  if (!batches?.length || batches.some((batch) => batch.status !== "completed")) return false;
  const rows = batches.flatMap((batch) => batch.rows ?? [])
    .sort((left, right) => Number(left.row_number) - Number(right.row_number));
  if (rows.length !== Number(job.total_rows)) throw new Error("Generated deck is incomplete.");

  const deckId = String(job.deck_id);
  const userId = String(job.user_id);
  const settings = job.settings as Record<string, unknown>;
  const level = settings.cefr_mode === "single"
    ? settings.single_level
    : `${settings.gradual_start}–${settings.gradual_end}`;
  const { error: deckError } = await admin.from("decks").insert({
    id: deckId,
    user_id: userId,
    title: job.title,
    source_language: job.source_language,
    translation_language: job.translation_language,
    cefr_level: level,
    settings,
    last_used_at: new Date().toISOString(),
  });
  if (deckError) throw deckError;
  try {
    for (let start = 0; start < rows.length; start += 200) {
      const { error } = await admin.from("cards").insert(rows.slice(start, start + 200).map((row) => ({
        id: crypto.randomUUID(),
        deck_id: deckId,
        user_id: userId,
        rank: row.row_number,
        foreign_word: row.foreign_word,
        word_translation: row.word_translation,
        foreign_sentence: row.foreign_sentence,
        sentence_translation: row.sentence_translation,
      })));
      if (error) throw error;
    }
  } catch (error) {
    await admin.from("decks").delete().eq("id", deckId);
    throw error;
  }
  const completedAt = new Date().toISOString();
  const fallbackBatches = batches.filter((batch) => batch.used_fallback).length;
  const inputTokens = batches.reduce((sum, batch) => sum + Number(batch.input_tokens ?? 0), 0);
  const outputTokens = batches.reduce((sum, batch) => sum + Number(batch.output_tokens ?? 0), 0);
  const generationLatencyMs = batches.reduce((sum, batch) => sum + Number(batch.latency_ms ?? 0), 0);
  await admin.from("mobile_generation_jobs").update({
    status: "completed", completed_rows: rows.length, completed_at: completedAt,
    updated_at: completedAt, error_message: null, fallback_batches: fallbackBatches,
    input_tokens: inputTokens, output_tokens: outputTokens,
    generation_latency_ms: generationLatencyMs,
  }).eq("id", jobId);
  await admin.from("mobile_generation_usage").update({ status: "completed", completed_at: completedAt }).eq("id", jobId);
  return true;
}

async function enqueueNext(functionUrl: string, serviceKey: string, jobId: string) {
  const response = await fetch(functionUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${serviceKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ action: "process", job_id: jobId }),
  });
  if (!response.ok) throw new Error(`Could not continue job: ${response.status}`);
}

async function processJob(
  admin: ReturnType<typeof createClient>,
  jobId: string,
  openAiKey: string,
  primaryModel: string,
  fallbackModel: string,
  functionUrl: string,
  serviceKey: string,
) {
  const { data: job, error: jobError } = await admin.from("mobile_generation_jobs").select("*").eq("id", jobId).single();
  if (jobError || !job || job.status === "completed" || job.status === "failed") return;
  await admin.from("mobile_generation_jobs").update({
    status: "running", started_at: job.started_at ?? new Date().toISOString(),
    updated_at: new Date().toISOString(), error_message: null,
  }).eq("id", jobId);

  const stale = new Date(Date.now() - 10 * 60 * 1000).toISOString();
  await admin.from("mobile_generation_batches").update({ status: "queued", error_message: null })
    .eq("job_id", jobId).eq("status", "running").lt("updated_at", stale);
  const { data: candidates, error: pendingError } = await admin.from("mobile_generation_batches")
    .select("batch_index,tasks").eq("job_id", jobId).eq("status", "queued")
    .order("batch_index").limit(parallelBatches);
  if (pendingError) throw pendingError;

  const claimed: Array<Record<string, unknown>> = [];
  for (const candidate of candidates ?? []) {
    const { data } = await admin.from("mobile_generation_batches")
      .update({
        status: "running", updated_at: new Date().toISOString(), started_at: new Date().toISOString(),
        provider_model: primaryModel, fallback_model: fallbackModel,
      })
      .eq("job_id", jobId).eq("batch_index", candidate.batch_index).eq("status", "queued")
      .select("batch_index,tasks").maybeSingle();
    if (data) claimed.push(data);
  }
  if (claimed.length === 0) {
    if (await finalizeJob(admin, job)) return;
    return;
  }

  const results = await Promise.allSettled(claimed.map(async (batch) => {
    const tasks = batch.tasks as Array<Record<string, unknown>>;
    const generated = await generateWithFallback(openAiKey, primaryModel, fallbackModel, job, tasks);
    const completedAt = new Date().toISOString();
    const { error } = await admin.from("mobile_generation_batches").update({
      status: "completed", rows: generated.rows, error_message: null, updated_at: completedAt,
      completed_at: completedAt, provider_model: generated.model, used_fallback: generated.usedFallback,
      attempt_count: generated.attempts, accepted_rows: generated.rows.length,
      input_tokens: generated.inputTokens, output_tokens: generated.outputTokens,
      latency_ms: generated.latencyMs, validation_errors: generated.validationErrors,
    }).eq("job_id", jobId).eq("batch_index", batch.batch_index);
    if (error) throw error;
  }));
  const failure = results.find((result) => result.status === "rejected") as PromiseRejectedResult | undefined;
  if (failure) {
    const message = failure.reason instanceof Error ? failure.reason.message : String(failure.reason);
    console.error("generation batch failed", message);
    await admin.from("mobile_generation_jobs").update({
      status: "failed", error_message: message, updated_at: new Date().toISOString(),
    }).eq("id", jobId);
    await admin.from("mobile_generation_usage").update({ status: "failed" }).eq("id", jobId);
    return;
  }
  const { data: complete } = await admin.from("mobile_generation_batches")
    .select("tasks").eq("job_id", jobId).eq("status", "completed");
  const completedRows = (complete ?? []).reduce((sum, batch) => sum + (batch.tasks?.length ?? 0), 0);
  await admin.from("mobile_generation_jobs").update({
    completed_rows: completedRows, updated_at: new Date().toISOString(),
  }).eq("id", jobId);
  if (!await finalizeJob(admin, job)) await enqueueNext(functionUrl, serviceKey, jobId);
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
  const primaryModel = Deno.env.get("OPENAI_MODEL") ?? "gpt-4o-mini";
  const fallbackModel = Deno.env.get("OPENAI_FALLBACK_MODEL") ?? "gpt-5.6-terra";
  if (!supabaseUrl || !anonKey || !serviceKey || !openAiKey) return json({ error: "The generation service is not configured correctly." }, 503);
  let body: Record<string, unknown>;
  try { body = await request.json(); } catch { return json({ error: "The generation request was not valid." }, 400); }
  const admin = createClient(supabaseUrl, serviceKey);
  const functionUrl = `${supabaseUrl}/functions/v1/generate-deck`;

  if (body.action === "process") {
    if (authorization !== `Bearer ${serviceKey}` || typeof body.job_id !== "string") return json({ error: "Not authorized." }, 401);
    // @ts-ignore EdgeRuntime is available in Supabase Edge Functions.
    EdgeRuntime.waitUntil(processJob(admin, body.job_id, openAiKey, primaryModel, fallbackModel, functionUrl, serviceKey));
    return json({ accepted: true }, 202);
  }

  const userClient = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authorization } } });
  const { data: { user }, error: userError } = await userClient.auth.getUser();
  if (userError || !user) return json({ error: "Your session expired. Sign in again." }, 401);
  if (body.action === "resume") {
    if (typeof body.job_id !== "string") return json({ error: "Choose a valid generation job." }, 400);
    const { data: job } = await admin.from("mobile_generation_jobs").select("id,status").eq("id", body.job_id).eq("user_id", user.id).maybeSingle();
    if (!job) return json({ error: "Generation job not found." }, 404);
    if (job.status === "queued" || job.status === "running") {
      // @ts-ignore EdgeRuntime is available in Supabase Edge Functions.
      EdgeRuntime.waitUntil(processJob(admin, job.id, openAiKey, primaryModel, fallbackModel, functionUrl, serviceKey));
    }
    return json({ accepted: true, status: job.status }, 202);
  }

  const learningCode = body.learning_language_code;
  const translationCode = body.translation_language_code;
  const learning = body.learning_language;
  const translation = body.translation_language;
  const title = body.title;
  const settings = body.settings;
  const tasks = body.tasks;
  if (typeof learningCode !== "string" || typeof translationCode !== "string" ||
      !allowedLanguages.has(learningCode) || !allowedLanguages.has(translationCode) || learningCode === translationCode ||
      typeof learning !== "string" || typeof translation !== "string" || typeof title !== "string" ||
      title.trim().length < 1 || title.trim().length > 200 || !settings || typeof settings !== "object" ||
      !Array.isArray(tasks) || tasks.length < 1 || tasks.length > 5000 ||
      !tasks.every((task) => task && typeof task === "object" && validTask(task))) {
    return json({ error: "Choose valid languages and generation settings." }, 400);
  }

  const { count: deckCount, error: countError } = await admin.from("decks").select("id", { count: "exact", head: true })
    .eq("user_id", user.id).eq("source_language", learning).is("deleted_at", null).is("mobile_removed_at", null);
  const { count: jobCount, error: jobCountError } = await admin.from("mobile_generation_jobs").select("id", { count: "exact", head: true })
    .eq("user_id", user.id).eq("source_language", learning).in("status", ["queued", "running"]);
  if (countError || jobCountError) return json({ error: "The deck limit could not be checked. Try again." }, 503);
  if ((deckCount ?? 0) + (jobCount ?? 0) >= 10) {
    return json({ error: `You already have 10 active ${learning} decks. Remove one before generating another.` }, 409);
  }

  const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const { data: recent, error: usageError } = await admin.from("mobile_generation_usage")
    .select("requested_rows").eq("user_id", user.id).gte("created_at", since);
  if (usageError) return json({ error: "The generation service is temporarily unavailable." }, 503);
  const used = (recent ?? []).reduce((sum, row) => sum + Number(row.requested_rows ?? 0), 0);
  if (used + tasks.length > 5000) return json({ error: "The 5,000-row mobile generation limit for the last 24 hours has been reached." }, 429);

  const jobId = crypto.randomUUID();
  const deckId = crypto.randomUUID();
  const { error: jobError } = await admin.from("mobile_generation_jobs").insert({
    id: jobId, user_id: user.id, deck_id: deckId, title: title.trim(),
    source_language: learning, source_language_code: learningCode,
    translation_language: translation, translation_language_code: translationCode,
    settings, tasks, total_rows: tasks.length,
    primary_model: primaryModel, fallback_model: fallbackModel,
  });
  if (jobError) return json({ error: "The generation job could not be created. Try again." }, 503);
  const batches = [];
  for (let start = 0; start < tasks.length; start += batchSize) {
    batches.push({ job_id: jobId, batch_index: Math.floor(start / batchSize), tasks: tasks.slice(start, start + batchSize) });
  }
  const { error: batchesError } = await admin.from("mobile_generation_batches").insert(batches);
  const { error: usageInsertError } = await admin.from("mobile_generation_usage").insert({
    id: jobId, user_id: user.id, requested_rows: tasks.length, status: "started",
  });
  if (batchesError || usageInsertError) {
    await admin.from("mobile_generation_jobs").delete().eq("id", jobId);
    return json({ error: "The generation job could not be queued. Try again." }, 503);
  }
  // @ts-ignore EdgeRuntime is available in Supabase Edge Functions.
  EdgeRuntime.waitUntil(processJob(admin, jobId, openAiKey, model, functionUrl, serviceKey));
  return json({ job_id: jobId, deck_id: deckId, status: "queued", total_rows: tasks.length }, 202);
});
