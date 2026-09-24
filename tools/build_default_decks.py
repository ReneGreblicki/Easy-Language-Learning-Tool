"""Generate a resumable, reviewable shared curriculum; never publish automatically.

Uses the pinned production English ranking and preserves its source attribution.
Run --pilot first. Full publication SQL requires a content-bound review manifest.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import os
import random
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID

try:
    from api_cost_guard import CostBudget
except ModuleNotFoundError:  # Imported directly by unit tests from the repository root.
    from tools.api_cost_guard import CostBudget

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources/frequency_data/production/words.jsonl.gz"
LANGUAGES = dict(
    re.findall(
        r"\w+\('([^']+)', '([^']+)'\)",
        (ROOT / "android_app/lib/generation/generation_settings.dart").read_text(),
    )
)
API_USAGE = {
    "requests": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "estimated_cost_usd": 0.0,
}
GOOGLE_USAGE = {"requests": 0, "cached_requests": 0, "characters": 0}
ACTIVE_BUDGET: CostBudget | None = None
MAX_COMPLETION_TOKENS = 4096
LAST_OPENAI_REQUEST_AT = 0.0
MAX_API_ATTEMPTS = 7
NON_RETRYABLE_429_CODES = {
    "billing_hard_limit_reached",
    "credit_balance_exhausted",
    "insufficient_quota",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
}

GOOGLE_TARGETS = {
    "es-ES": "es",
    "de-DE": "de",
    "pt-PT": "pt",
    "fr-FR": "fr",
    "it-IT": "it",
    "th-Thai-TH": "th",
    "pl-PL": "pl",
    "nl-NL": "nl",
    "da-DK": "da",
    "hr-HR": "hr",
    "vi-VN": "vi",
    "zh-CN": "zh-CN",
    "ml-IN": "ml",
    "sk-SK": "sk",
    "ru-RU": "ru",
    "nb-NO": "no",
    "ko-KR": "ko",
    "hu-HU": "hu",
    "sv-SE": "sv",
    "id-ID": "id",
    "ja-JP": "ja",
    "tr-TR": "tr",
}


def record_usage(payload: dict, model: str) -> None:
    usage = payload.get("usage", {})
    API_USAGE["requests"] += 1
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        API_USAGE[key] += int(usage.get(key, 0))
    if ACTIVE_BUDGET:
        API_USAGE["estimated_cost_usd"] = round(ACTIVE_BUDGET.record(model, usage), 8) + float(
            API_USAGE["estimated_cost_usd"]
        )


def preflight_request(model: str, body: bytes) -> None:
    if ACTIVE_BUDGET:
        ACTIVE_BUDGET.preflight(model, body, MAX_COMPLETION_TOKENS)


def generation_options(
    model: str, reasoning_effort: str | None, temperature: float
) -> dict[str, object]:
    """Return API options accepted by both reasoning and non-reasoning models."""
    if reasoning_effort:
        return {"reasoning_effort": reasoning_effort}
    return {"temperature": temperature}


def retry_delay(error: Exception, attempt: int) -> float:
    if isinstance(error, urllib.error.HTTPError) and error.code == 429:
        try:
            server_delay = float(error.headers.get("Retry-After", 0))
        except (TypeError, ValueError):
            server_delay = 0.0
        return max(server_delay, min(180.0, 10.0 * (2**attempt))) + random.uniform(0.0, 2.0)
    return float(2**attempt)


def openai_error_details(error: urllib.error.HTTPError) -> dict[str, str]:
    """Extract safe diagnostics so permanent 429s are not retried blindly."""
    try:
        payload = json.loads(error.read().decode("utf-8", errors="replace"))
        details = payload.get("error", {})
        return {
            "type": str(details.get("type") or ""),
            "code": str(details.get("code") or ""),
            "message": str(details.get("message") or "")[:500],
        }
    except (AttributeError, json.JSONDecodeError, OSError):
        return {"type": "", "code": "", "message": ""}


def retryable_http_error(error: urllib.error.HTTPError, details: dict[str, str]) -> bool:
    if error.code == 503:
        return True
    return error.code == 429 and details.get("code") not in NON_RETRYABLE_429_CODES


def pace_openai_requests() -> None:
    """Keep bulk generation steady instead of bursting into project limits."""
    global LAST_OPENAI_REQUEST_AT
    interval = max(0.0, float(os.environ.get("OPENAI_REQUEST_INTERVAL_SECONDS", "6")))
    remaining = interval - (time.monotonic() - LAST_OPENAI_REQUEST_AT)
    if LAST_OPENAI_REQUEST_AT and remaining > 0:
        time.sleep(remaining)
    LAST_OPENAI_REQUEST_AT = time.monotonic()


def request_timeout(reasoning_effort: str | None) -> int:
    return 300 if reasoning_effort else 120


def translate_google_sentences(values: list[str], target: str, api_key: str) -> list[str]:
    """Translate one paid batch without automatic retries or putting the key in the URL."""
    body = json.dumps({"q": values, "source": "en", "target": target, "format": "text"}).encode()
    request = urllib.request.Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=body,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    translations = payload["data"]["translations"]
    if len(translations) != len(values):
        raise ValueError("Google Translation returned an incomplete sentence batch")
    return [html.unescape(row["translatedText"]) for row in translations]


def google_draft_rows(
    tasks: list[dict],
    code: str,
    api_key: str,
    checkpoint_dir: Path,
) -> list[dict]:
    values = [row["sentence"] for row in tasks]
    digest = hashlib.sha256(
        json.dumps(["google-sentence-v1", code, values], ensure_ascii=False).encode()
    ).hexdigest()[:24]
    checkpoint = checkpoint_dir / f"google-draft-{code}-{digest}.json"
    GOOGLE_USAGE["characters"] += sum(len(value) for value in values)
    if checkpoint.exists():
        translated = json.loads(checkpoint.read_text(encoding="utf-8"))
        GOOGLE_USAGE["cached_requests"] += 1
    else:
        translated = translate_google_sentences(values, GOOGLE_TARGETS[code], api_key)
        checkpoint.write_text(
            json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        GOOGLE_USAGE["requests"] += 1
    return [
        {
            "id": task["id"],
            "word": "(select the natural dictionary headword)",
            "sentence": translated[index],
            "sense": task["sense"],
        }
        for index, task in enumerate(tasks)
    ]


def frequency_candidates(sentence: str, rows: list[dict], limit: int = 12) -> list[dict]:
    """Return high-frequency corpus entries visible in a Google draft."""
    haystack = normalize(sentence)
    matches = []
    for row in rows[:5000]:
        lemma = normalize(row["lemma"])
        visible = (
            bool(re.search(rf"(?<!\w){re.escape(lemma)}(?!\w)", haystack))
            if lemma.isascii()
            else lemma in haystack
        )
        if lemma and visible:
            matches.append({"lemma": row["lemma"], "rank": row["rank"]})
            if len(matches) == limit:
                break
    return matches


def stable_id(value: str) -> str:
    return str(UUID(hashlib.md5(value.encode(), usedforsecurity=False).hexdigest()))


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def frequency_data() -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            result.setdefault(row["language"], []).append(row)
    for rows in result.values():
        rows.sort(key=lambda row: row["rank"])
    return result


def request_rows(
    tasks: list[dict], language: str, model: str, reasoning_effort: str | None = None
) -> list[dict]:
    instruction = (
        "Return one row per input id with target_word, target_sentence, and sense_in_english. "
        "All target_word and target_sentence values MUST be in " + language + ". "
        "sense_in_english MUST be English. Never copy an untranslated source headword. "
        "Use natural adult-neutral examples at the specified CEFR level. A1: simple concrete "
        "sentences; A2: everyday situations; B1: two connected ideas, such as a reason, "
        "contrast, experience or opinion, not a single elementary clause. Target sentences must use "
        "the target headword or its grammatical inflection. Preserve concepts and IDs. "
    )
    if language == "US English":
        instruction += "Keep each input word exactly. Write one original sentence using it and identify its common intended meaning. "
    elif language == "Thai (Paiboon romanization)":
        instruction += (
            "Transliterate the supplied Thai headwords and sentences into Paiboon "
            "romanization with appropriate vowel symbols and tone marks. Follow spellings like "
            "châi, mâi, kráp, nîi, kɔ̀ɔp-kun, dtɛ̀ɛ, à-rai. Use diacritics for tones, "
            "not unmarked ASCII approximations like thi, chan or tongkan. NO Thai characters "
            "anywhere in target_word or target_sentence. Do not translate them into English. "
        )
    else:
        instruction += (
            "Translate BOTH the source word AND its sentence. Preserve the exact subject, object, "
            "action and intended sense; never change a cat into a dog or copy nouns from these "
            "instructions. Avoid using a target headword that is absent from your sentence. "
            "For example English "
            "'the' in German can be target_word 'die' in 'Die Katze ...'; in Spanish 'el' in "
            "'El gato ...'. When no standalone equivalent exists, use a natural contextual "
            "phrase in the target language that expresses that meaning. For Thai, the English "
            "definite article has no standalone equivalent: translate the definite noun phrase "
            "instead, e.g. the dog as สุนัขตัวนั้น, and use that phrase in the sentence. "
            "Do not substitute an unrelated Thai word merely to fill the headword field. Do not retain the "
            "English headword as a label. Adapt grammar naturally while preserving meaning. "
        )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "target_word", "target_sentence", "sense_in_english"],
                    "properties": {
                        "id": {"type": "integer"},
                        "target_word": {"type": "string"},
                        "target_sentence": {"type": "string"},
                        "sense_in_english": {"type": "string"},
                    },
                },
            }
        },
    }
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(tasks, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "learning_rows", "strict": True, "schema": schema},
            },
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            **generation_options(model, reasoning_effort, 0.2),
        }
    ).encode()
    preflight_request(model, body)
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            preflight_request(model, body)
            pace_openai_requests()
            with urllib.request.urlopen(
                request, timeout=request_timeout(reasoning_effort)
            ) as response:
                payload = json.load(response)
            record_usage(payload, model)
            raw = json.loads(payload["choices"][0]["message"]["content"])["rows"]
            rows = [
                {
                    "id": r["id"],
                    "word": r["target_word"],
                    "sentence": r["target_sentence"],
                    "sense": r["sense_in_english"],
                }
                for r in raw
            ]
            validate_rows(rows, tasks)
            validate_language(rows, tasks, language)
            return rows
        except (ValueError, KeyError, OSError) as error:
            if isinstance(error, urllib.error.HTTPError):
                details = openai_error_details(error)
                print(
                    "OpenAI API error: "
                    f"status={error.code} type={details['type']!r} code={details['code']!r} "
                    f"message={details['message']!r}",
                    flush=True,
                )
                if not retryable_http_error(error, details):
                    raise RuntimeError(
                        f"OpenAI API request requires account action: {details['code'] or error.code}"
                    ) from error
            if attempt == MAX_API_ATTEMPTS - 1:
                raise
            if isinstance(error, (ValueError, KeyError)):
                retry_body = json.loads(body)
                retry_body["messages"].append(
                    {
                        "role": "user",
                        "content": "The previous response failed validation: "
                        + str(error)
                        + ". Correct the entire batch.",
                    }
                )
                body = json.dumps(retry_body, ensure_ascii=False).encode()
                request.data = body
            time.sleep(retry_delay(error, attempt))
    raise AssertionError("unreachable")


def review_rows(
    tasks: list[dict],
    draft_rows: list[dict],
    language: str,
    model: str,
    reasoning_effort: str | None = None,
) -> list[dict]:
    """Apply a separate editorial pass before accepting translated content."""
    instruction = (
        "You are the final language editor for a frequency-based learning curriculum. "
        "Return one corrected row per id with target_word, target_sentence, and "
        "sense_in_english. Review the draft rather than merely repeating it. The target "
        "word and sentence must be natural " + language + ", express exactly the source "
        "meaning and proposition, and be appropriate for the supplied CEFR level. Preserve "
        "the exact sense_in_english text from the source. Use a useful dictionary headword "
        "when one exists; grammatical inflection in the sentence is allowed. For English "
        "function words without a direct standalone equivalent, use the shortest natural "
        "contextual equivalent or construction—never force an ungrammatical marker. Correct "
        "literal calques, altered subjects/objects/actions, unnatural register, and sentences "
        "that do not demonstrate the study item. B1 examples must contain two connected ideas. "
        "The draft sentence may come from Google Cloud Translation. Keep it when it is accurate "
        "and natural; otherwise make the smallest necessary correction. Select the dictionary "
        "headword for the supplied English sense. Prefer a ranked_target_candidate only when it "
        "expresses that exact sense; never choose a frequent but semantically unrelated word. "
    )
    if language == "Thai (Paiboon romanization)":
        instruction += (
            "Use tone-marked Paiboon romanization only, with no Thai characters. Preserve "
            "the supplied Thai meaning and use consistent spellings such as châi, mâi, kráp, "
            "nîi, kɔ̀ɔp-kun, dtɛ̀ɛ and à-rai. "
        )
    drafts_by_id = {row["id"]: row for row in draft_rows}
    payload_rows = [
        {
            "id": task["id"],
            "level": task["level"],
            "source_word": task["word"],
            "source_sentence": task["sentence"],
            "sense_in_english": task["sense"],
            "draft_target_word": drafts_by_id[task["id"]]["word"],
            "draft_target_sentence": drafts_by_id[task["id"]]["sentence"],
            "ranked_target_candidates": task.get("ranked_target_candidates", []),
        }
        for task in tasks
    ]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "target_word",
                        "target_sentence",
                        "sense_in_english",
                    ],
                    "properties": {
                        "id": {"type": "integer"},
                        "target_word": {"type": "string"},
                        "target_sentence": {"type": "string"},
                        "sense_in_english": {"type": "string"},
                    },
                },
            }
        },
    }
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(payload_rows, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "reviewed_learning_rows",
                    "strict": True,
                    "schema": schema,
                },
            },
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            **generation_options(model, reasoning_effort, 0.1),
        },
        ensure_ascii=False,
    ).encode()
    preflight_request(model, body)
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    for attempt in range(MAX_API_ATTEMPTS):
        try:
            preflight_request(model, body)
            pace_openai_requests()
            with urllib.request.urlopen(
                request, timeout=request_timeout(reasoning_effort)
            ) as response:
                payload = json.load(response)
            record_usage(payload, model)
            raw = json.loads(payload["choices"][0]["message"]["content"])["rows"]
            rows = [
                {
                    "id": row["id"],
                    "word": row["target_word"],
                    "sentence": row["target_sentence"],
                    "sense": row["sense_in_english"],
                }
                for row in raw
            ]
            validate_rows(rows, tasks)
            validate_language(rows, tasks, language)
            return rows
        except (ValueError, KeyError, OSError) as error:
            if isinstance(error, urllib.error.HTTPError):
                details = openai_error_details(error)
                print(
                    "OpenAI API error: "
                    f"status={error.code} type={details['type']!r} code={details['code']!r} "
                    f"message={details['message']!r}",
                    flush=True,
                )
                if not retryable_http_error(error, details):
                    raise RuntimeError(
                        f"OpenAI API request requires account action: {details['code'] or error.code}"
                    ) from error
            if attempt == MAX_API_ATTEMPTS - 1:
                raise
            if isinstance(error, (ValueError, KeyError)):
                retry_body = json.loads(body)
                retry_body["messages"].append(
                    {
                        "role": "user",
                        "content": "The editorial response failed validation: "
                        + str(error)
                        + ". Return the complete corrected batch.",
                    }
                )
                body = json.dumps(retry_body, ensure_ascii=False).encode()
                request.data = body
            time.sleep(retry_delay(error, attempt))
    raise AssertionError("unreachable")


def validate_rows(rows: list[dict], tasks: list[dict]) -> None:
    if len(rows) != len(tasks) or {r["id"] for r in rows} != {t["id"] for t in tasks}:
        raise ValueError("Missing or duplicated concept IDs")
    for row in rows:
        if any(
            not isinstance(row.get(key), str) or not row[key].strip()
            for key in ("word", "sentence", "sense")
        ):
            raise ValueError("Empty word, sentence or sense")
        if len(row["sentence"]) > 1000 or len(row["word"]) > 160:
            raise ValueError("Unexpectedly long content")


def validate_language(rows: list[dict], tasks: list[dict], language: str) -> None:
    original = {t["id"]: t for t in tasks}
    if language == "US English":
        if any(normalize(r["word"]) != normalize(original[r["id"]]["word"]) for r in rows):
            raise ValueError("English generation changed a source word")
    elif len(rows) >= 5:
        copied = sum(normalize(r["word"]) == normalize(original[r["id"]]["word"]) for r in rows)
        if copied / len(rows) > 0.6:
            raise ValueError("Most headwords were not translated")
        if any(
            "sense" in original[row["id"]]
            and normalize(row["sense"]) != normalize(original[row["id"]]["sense"])
            for row in rows
        ):
            raise ValueError("English sense changed during translation")
    if language == "Thai (Paiboon romanization)":
        combined = unicodedata.normalize("NFD", " ".join(r["sentence"] for r in rows))
        if not any(mark in combined for mark in ("\u0300", "\u0301", "\u0302", "\u030c")):
            raise ValueError("Paiboon sentences lack tone marks; unmarked ASCII is not accepted")
    for row in rows:
        for key in ("word", "sentence"):
            thai = bool(re.search(r"[\u0e00-\u0e7f]", row[key]))
            if language == "Thai (Paiboon romanization)" and thai:
                raise ValueError("Thai script found in romanization")
            if language == "Thai (Thai script)" and not thai:
                raise ValueError("Thai script missing from native translation")


def generate(
    output: Path,
    pilot: bool,
    languages: list[str],
    model: str,
    reasoning_effort: str | None = None,
    editorial_mode: str = "selective",
    max_cost_usd: float = 4.0,
    pipeline: str = "hybrid",
    max_google_characters: int = 950_000,
    max_google_requests: int = 1100,
) -> dict:
    global ACTIVE_BUDGET
    started = time.monotonic()
    if pipeline == "hybrid" and not os.environ.get("GOOGLE_TRANSLATE_API_KEY"):
        raise ValueError("GOOGLE_TRANSLATE_API_KEY is required for the hybrid pipeline")
    worst_case_google_usd = max_google_characters * 20.0 / 1_000_000
    if pipeline == "hybrid" and max_cost_usd + worst_case_google_usd > 23.0:
        raise ValueError(
            "Hybrid generation caps exceed the reserved $23 build budget: "
            f"openai=${max_cost_usd:.2f}, google=${worst_case_google_usd:.2f}"
        )
    for key in API_USAGE:
        API_USAGE[key] = 0
    for key in GOOGLE_USAGE:
        GOOGLE_USAGE[key] = 0
    ACTIVE_BUDGET = CostBudget(max_cost_usd)
    frequencies = frequency_data()
    english = frequencies["en-US"][:1000]
    if len(english) != 1000 or len({r["rank"] for r in english}) != 1000:
        raise ValueError("Expected 1,000 English source entries")
    tasks = [
        {
            "id": r["rank"],
            "word": r["lemma"],
            "level": "A1" if r["rank"] <= 400 else "A2" if r["rank"] <= 700 else "B1",
        }
        for r in english
        if not pilot or r["rank"] in {*range(1, 11), *range(401, 411), *range(701, 711)}
    ]
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "checkpoints"
    checkpoint.mkdir(exist_ok=True)
    datasets = {}
    hybrid_evidence: list[dict] = []
    ordered = list(dict.fromkeys(["en-US", *languages]))
    if "th-Latn-TH" in ordered:
        if "th-Thai-TH" in ordered:
            ordered.remove("th-Thai-TH")
        ordered.insert(ordered.index("th-Latn-TH"), "th-Thai-TH")
    google_plan_checked = False
    for code in ordered:
        if code not in LANGUAGES:
            raise ValueError(f"Unknown language: {code}")
        source_tasks = (
            tasks
            if code == "en-US"
            else datasets["th-Thai-TH" if code == "th-Latn-TH" else "en-US"]
        )
        generated = []
        for start in range(0, len(source_tasks), 20):
            batch = source_tasks[start : start + 20]
            # Changing input/model invalidates the checkpoint rather than silently reusing it.
            digest = hashlib.sha256(
                json.dumps(
                    [
                        "prompt-v7-hybrid",
                        pipeline,
                        model,
                        reasoning_effort,
                        editorial_mode,
                        code,
                        batch,
                    ],
                    sort_keys=True,
                ).encode()
            ).hexdigest()[:20]
            file = checkpoint / f"{code}-{digest}.json"
            evidence_file = checkpoint / f"{code}-{digest}.evidence.json"
            batch_evidence: list[dict] = []
            cache_valid = file.exists() and (
                pipeline != "hybrid" or code == "en-US" or evidence_file.exists()
            )
            if cache_valid:
                rows = json.loads(file.read_text())
                if evidence_file.exists():
                    batch_evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
            elif pipeline == "hybrid" and code in GOOGLE_TARGETS:
                drafts = google_draft_rows(
                    batch, code, os.environ["GOOGLE_TRANSLATE_API_KEY"], checkpoint
                )
                enriched = [
                    {
                        **task,
                        "ranked_target_candidates": frequency_candidates(
                            drafts[index]["sentence"], frequencies[code]
                        ),
                    }
                    for index, task in enumerate(batch)
                ]
                rows = review_rows(enriched, drafts, LANGUAGES[code], model, reasoning_effort)
                for task, draft, row in zip(batch, drafts, rows, strict=True):
                    batch_evidence.append(
                        {
                            "language": code,
                            "id": row["id"],
                            "draft_provider": "google-cloud-translation-v2",
                            "editor_model": model,
                            "source_sha256": hashlib.sha256(
                                (
                                    task["word"] + "\n" + task["sentence"] + "\n" + task["sense"]
                                ).encode()
                            ).hexdigest(),
                            "google_draft_sentence": draft["sentence"],
                            "target_sha256": hashlib.sha256(
                                (row["word"] + "\n" + row["sentence"]).encode()
                            ).hexdigest(),
                        }
                    )
            else:
                rows = request_rows(batch, LANGUAGES[code], model, reasoning_effort)
                if code == "th-Latn-TH" and pipeline == "hybrid":
                    for task, row in zip(batch, rows, strict=True):
                        batch_evidence.append(
                            {
                                "language": code,
                                "id": row["id"],
                                "draft_provider": "thai-script-specialized",
                                "editor_model": model,
                                "source_sha256": hashlib.sha256(
                                    (
                                        task["word"]
                                        + "\n"
                                        + task["sentence"]
                                        + "\n"
                                        + task["sense"]
                                    ).encode()
                                ).hexdigest(),
                                "target_sha256": hashlib.sha256(
                                    (row["word"] + "\n" + row["sentence"]).encode()
                                ).hexdigest(),
                            }
                        )
            if (
                not cache_valid
                and code != "en-US"
                and editorial_mode == "full"
                and pipeline != "hybrid"
            ):
                rows = review_rows(batch, rows, LANGUAGES[code], model, reasoning_effort)
            validate_rows(rows, batch)
            validate_language(rows, batch, LANGUAGES[code])
            file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            if batch_evidence:
                evidence_file.write_text(
                    json.dumps(batch_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                hybrid_evidence.extend(batch_evidence)
            by_id = {r["id"]: r for r in rows}
            generated.extend({**by_id[t["id"]], "level": t["level"]} for t in batch)
        lookup = {normalize(r["lemma"]): r["rank"] for r in frequencies[code]}
        for row in generated:
            row["source_rank"] = lookup.get(normalize(row["word"]))
        for level in ("A1", "A2", "B1"):
            group = sorted(
                (r for r in generated if r["level"] == level),
                key=lambda r: (r["source_rank"] or 99999, r["id"]),
            )
            for rank, row in enumerate(group, 1):
                row["rank"] = rank
        datasets[code] = generated
        if pipeline == "hybrid" and code == "en-US" and not google_plan_checked:
            google_codes = [item for item in ordered if item in GOOGLE_TARGETS]
            planned_characters = sum(len(row["sentence"]) for row in generated) * len(google_codes)
            planned_requests = ((len(generated) + 19) // 20) * len(google_codes)
            if planned_characters > max_google_characters or planned_requests > max_google_requests:
                raise RuntimeError(
                    "Google Translation hard cap blocks this run before any request: "
                    f"characters={planned_characters}/{max_google_characters}, "
                    f"requests={planned_requests}/{max_google_requests}"
                )
            google_plan_checked = True
    result = {
        "pilot": pilot,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "editorial_mode": editorial_mode,
        "pipeline": pipeline,
        "max_cost_usd": max_cost_usd,
        "max_google_characters": max_google_characters,
        "max_google_requests": max_google_requests,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_attribution": {
            k: english[0].get(k) for k in ("source", "licence", "source_url", "source_revision")
        },
        "api_usage": dict(API_USAGE),
        "google_usage": dict(GOOGLE_USAGE),
        "languages": datasets,
    }
    content = json.dumps(result, ensure_ascii=False, indent=2)
    (output / "curriculum.json").write_text(content, encoding="utf-8")
    if pipeline == "hybrid":
        (output / "hybrid_evidence.json").write_text(
            json.dumps(
                {
                    "pipeline": "google-draft-gpt-post-edit-v1",
                    "rows": hybrid_evidence,
                    "google_usage": dict(GOOGLE_USAGE),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    (output / "language_codes.json").write_text(
        json.dumps(list(LANGUAGES), indent=2), encoding="utf-8"
    )
    issues = [
        f"{code} concept {r['id']}: translation not matched to ranked source"
        for code, rows in datasets.items()
        for r in rows
        if r["source_rank"] is None
    ]
    review_lines = [
        "# Curriculum pilot review",
        "",
        "Draft, not published. Check sense alignment, naturalness, target-word inclusion, CEFR suitability and script.",
        "",
    ]
    for code, rows in datasets.items():
        review_lines.extend(
            [
                "## " + LANGUAGES[code],
                "",
                "| Concept | Level | Word | Sentence | English meaning |",
                "|---|---|---|---|---|",
            ]
        )
        for row in rows:
            cells = [str(row["id"]), row["level"], row["word"], row["sentence"], row["sense"]]
            review_lines.append(
                "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"
            )
        review_lines.append("")
    review_lines.extend(["## Ranking matches to review", "", *["- " + i for i in issues]])
    review_text = "\n".join(review_lines)
    (output / "review.md").write_text(review_text, encoding="utf-8")
    if pilot and os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(review_text, encoding="utf-8")
    return result


def publication_sql(curriculum: Path, review: Path, version: int) -> str:
    content = curriculum.read_bytes()
    data, approval = json.loads(content), json.loads(review.read_text())
    if data["pilot"] or version < 1:
        raise ValueError("Only complete curricula with a positive version can be published")
    if (
        approval.get("sha256") != hashlib.sha256(content).hexdigest()
        or not approval.get("reviewer")
        or not approval.get("approved")
    ):
        raise ValueError("A review bound to this exact curriculum is required")
    if set(data["languages"]) != set(LANGUAGES):
        raise ValueError("All supported language/script options must be present")
    for rows in data["languages"].values():
        validate_rows(rows, [{"id": i} for i in range(1, 1001)])
        for level, count in [("A1", 400), ("A2", 300), ("B1", 300)]:
            group = [r for r in rows if r["level"] == level]
            if len(group) != count or sorted(r["rank"] for r in group) != list(range(1, count + 1)):
                raise ValueError("Invalid level counts or ordering")
        levels = {r["id"]: r["level"] for r in rows}
        if levels != {r["id"]: r["level"] for r in data["languages"]["en-US"]}:
            raise ValueError("Concept levels must align between languages")

    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    sql = ["begin;", "-- Reviewed shared content; personal decks are untouched."]
    for row in data["languages"]["en-US"]:
        values = [
            str(row["id"]),
            quote(row["level"]),
            quote(row["word"]),
            quote(row["sentence"]),
            quote(row["sense"]),
        ]
        sql.append(
            "insert into public.default_concepts(id,default_level,english_word,english_sentence,sense) values ("
            + ",".join(values)
            + ") on conflict(id) do update set english_word=excluded.english_word,english_sentence=excluded.english_sentence,sense=excluded.sense;"
        )
    for code, rows in data["languages"].items():
        for row in rows:
            deck = stable_id("default:" + LANGUAGES[code] + ":" + row["level"])
            card = stable_id("default-card:" + code + ":" + str(row["id"]))
            sql.append(
                f"insert into public.default_card_identity(id,deck_id,concept_id) values('{card}','{deck}',{row['id']}) on conflict(id) do nothing;"
            )
            sql.append(
                "insert into public.default_translations(card_id,content_version,word,sentence,rank,source_rank) values("
                + ",".join(
                    [
                        quote(card),
                        str(version),
                        quote(row["word"]),
                        quote(row["sentence"]),
                        str(row["rank"]),
                        str(row["source_rank"]) if row["source_rank"] else "null",
                    ]
                )
                + ");"
            )
    sql.extend([f"update public.default_decks set content_version={version};", "commit;"])
    return "\n".join(sql) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--languages", nargs="+", default=list(LANGUAGES))
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument(
        "--pipeline",
        choices=("hybrid", "direct"),
        default="hybrid",
        help="Hybrid uses Google sentence drafts followed by model post-editing.",
    )
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=4.0,
        help="Hard preflight budget for this generator process.",
    )
    parser.add_argument("--max-google-characters", type=int, default=950_000)
    parser.add_argument("--max-google-requests", type=int, default=1100)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
    )
    parser.add_argument(
        "--editorial-mode",
        choices=("selective", "full"),
        default="selective",
        help="Use full for the legacy all-row second pass; selective defers review to the cost-gated pipeline.",
    )
    parser.add_argument("--review", type=Path)
    parser.add_argument("--version", type=int, default=1)
    args = parser.parse_args()
    if args.review:
        sql = publication_sql(args.output / "curriculum.json", args.review, args.version)
        (args.output / "publish.sql").write_text(sql, encoding="utf-8")
    else:
        try:
            generate(
                args.output,
                args.pilot,
                args.languages,
                args.model,
                args.reasoning_effort,
                args.editorial_mode,
                args.max_cost_usd,
                args.pipeline,
                args.max_google_characters,
                args.max_google_requests,
            )
        finally:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "api_usage.json").write_text(
                json.dumps(API_USAGE, indent=2), encoding="utf-8"
            )
            (args.output / "google_usage.json").write_text(
                json.dumps(GOOGLE_USAGE, indent=2), encoding="utf-8"
            )


if __name__ == "__main__":
    main()
