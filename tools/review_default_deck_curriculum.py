"""Cost-gated automated review, repair, and independent translation checks.

The expensive model sees only rows flagged by deterministic checks. Google Cloud
Translation is used only as an independent back-translation source. Final release
approval is delegated to ``default_deck_quality.py``, which has no network code.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import default_deck_quality as quality

ROOT = Path(__file__).resolve().parents[1]

REPAIRABLE_CODES = {
    "missing_content",
    "placeholder",
    "sense_drift",
    "english_word_changed",
    "missing_script",
    "mixed_thai_script",
    "missing_tone_marks",
    "headword_not_in_top_5000",
    "headword_not_verbatim",
    "possible_untranslated_word",
    "number_drift",
    "backtranslation_conflict",
    "backtranslation_low_agreement",
    "backtranslated_word_conflict",
}


def request_json(request: urllib.request.Request, attempts: int = 4) -> dict:
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if attempt == attempts - 1 or error.code not in {429, 500, 502, 503, 504}:
                raise
            try:
                delay = max(2.0, float(error.headers.get("Retry-After", 0)))
            except (TypeError, ValueError):
                delay = float(2**attempt)
            time.sleep(delay)
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def translate_google(values: list[str], target: str, api_key: str) -> list[str]:
    body = urllib.parse.urlencode(
        [("q", value) for value in values] + [("target", target), ("format", "text")]
    ).encode()
    request = urllib.request.Request(
        "https://translation.googleapis.com/language/translate/v2?key="
        + urllib.parse.quote(api_key, safe=""),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    payload = request_json(request)
    translations = payload["data"]["translations"]
    if len(translations) != len(values):
        raise ValueError("Google Translation returned an incomplete batch")
    return [html.unescape(row["translatedText"]) for row in translations]


def build_backtranslations(
    curriculum: dict,
    api_key: str,
    only: set[tuple[str, int]] | None = None,
) -> tuple[dict, dict]:
    output = []
    characters = 0
    for code, rows in curriculum["languages"].items():
        if code == "en-US":
            continue
        selected = [row for row in rows if only is None or (code, row["id"]) in only]
        for start in range(0, len(selected), 50):
            batch = selected[start : start + 50]
            values = [value for row in batch for value in (row["word"], row["sentence"])]
            characters += sum(len(value) for value in values)
            translated = translate_google(values, "en", api_key)
            for index, row in enumerate(batch):
                output.append(
                    {
                        "language": code,
                        "id": row["id"],
                        "provider": "google-cloud-translation-v2",
                        "source_sha256": hashlib.sha256(
                            (row["word"] + "\n" + row["sentence"]).encode()
                        ).hexdigest(),
                        "backtranslated_word": translated[index * 2],
                        "backtranslated_sentence": translated[index * 2 + 1],
                    }
                )
    return {"provider": "google-cloud-translation-v2", "rows": output}, {
        "requests": sum(
            (len([row for row in rows if only is None or (code, row["id"]) in only]) + 49) // 50
            for code, rows in curriculum["languages"].items()
            if code != "en-US"
        ),
        "characters": characters,
        "rows": len(output),
    }


def repair_schema() -> dict:
    properties = {
        "language": {"type": "string"},
        "id": {"type": "integer"},
        "target_word": {"type": "string"},
        "target_sentence": {"type": "string"},
        "sense_in_english": {"type": "string"},
        "explanation": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(properties),
                    "properties": properties,
                },
            }
        },
    }


def repair_rows(
    curriculum: dict,
    report: dict,
    model: str,
    api_key: str,
    accepted_codes: set[str] = REPAIRABLE_CODES,
    errors_only: bool = False,
) -> tuple[list[dict], dict]:
    source = {row["id"]: row for row in curriculum["languages"]["en-US"]}
    by_language = {
        code: {row["id"]: row for row in rows} for code, rows in curriculum["languages"].items()
    }
    reasons: dict[tuple[str, int], set[str]] = defaultdict(set)
    for finding in report["findings"]:
        key = (finding["language"], finding["concept_id"])
        if (
            finding["repairable"]
            and finding["code"] in accepted_codes
            and key[0] != "*"
            and (not errors_only or finding["severity"] == "error")
        ):
            reasons[key].add(finding["code"])
    candidates = []
    for (code, concept_id), codes in sorted(reasons.items()):
        draft = by_language[code][concept_id]
        original = source[concept_id]
        candidates.append(
            {
                "language": code,
                "id": concept_id,
                "level": draft["level"],
                "source_word": original["word"],
                "source_sentence": original["sentence"],
                "sense_in_english": original["sense"],
                "draft_target_word": draft["word"],
                "draft_target_sentence": draft["sentence"],
                "detected_problems": sorted(codes),
            }
        )
    if not candidates:
        return [], {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    instruction = (
        "Act as a multilingual correction editor. Correct every supplied row independently. "
        "Preserve language, id, exact English sense, proposition, subject, object, action, numbers, "
        "and CEFR level. Return a natural target-language dictionary headword or short construction "
        "that is demonstrated in the sentence. Never return '-', 'no equivalent', an untranslated "
        "English label, or a word unrelated to the source sense. For Thai romanization use tone-marked "
        "Paiboon and no Thai script. Make the smallest correction that resolves all detected problems."
    )
    repaired: list[dict] = []
    usage = defaultdict(int)
    for start in range(0, len(candidates), 24):
        batch = candidates[start : start + 24]
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
            ],
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "corrected_rows",
                    "strict": True,
                    "schema": repair_schema(),
                },
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        )
        payload = request_json(request)
        rows = json.loads(payload["choices"][0]["message"]["content"])["rows"]
        expected = {(row["language"], row["id"]) for row in batch}
        actual = {(row["language"], row["id"]) for row in rows}
        if actual != expected or len(rows) != len(expected):
            raise ValueError("Repair model omitted, duplicated, or added rows")
        repaired.extend(rows)
        provider_usage = payload.get("usage", {})
        usage["requests"] += 1
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage[key] += int(provider_usage.get(key, 0))
    return repaired, dict(usage)


def apply_repairs(curriculum: dict, repaired: list[dict], corpus_path: Path) -> dict:
    indexes, _ = quality.load_corpus(corpus_path)
    by_key = {(row["language"], row["id"]): row for row in repaired}
    result = json.loads(json.dumps(curriculum))
    for code, rows in result["languages"].items():
        for row in rows:
            replacement = by_key.get((code, row["id"]))
            if not replacement:
                continue
            row["word"] = replacement["target_word"].strip()
            row["sentence"] = replacement["target_sentence"].strip()
            row["sense"] = replacement["sense_in_english"].strip()
            corpus_row = indexes.get(code, {}).get(quality.corpus_normalized(row["word"]))
            row["source_rank"] = corpus_row["rank"] if corpus_row else None
    return result


def reconcile_source_ranks(curriculum: dict, corpus_path: Path) -> int:
    indexes, _ = quality.load_corpus(corpus_path)
    changes = 0
    for code, rows in curriculum["languages"].items():
        for row in rows:
            corpus_row = indexes.get(code, {}).get(quality.corpus_normalized(row["word"]))
            expected = corpus_row["rank"] if corpus_row else None
            if row.get("source_rank") != expected:
                row["source_rank"] = expected
                changes += 1
    return changes


def merge_backtranslations(existing: dict, updates: dict) -> dict:
    rows = {(row["language"], row["id"]): row for row in existing.get("rows", [])}
    rows.update({(row["language"], row["id"]): row for row in updates.get("rows", [])})
    return {
        "provider": existing.get("provider", updates.get("provider")),
        "rows": list(rows.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=quality.DEFAULT_CORPUS)
    parser.add_argument("--repair-model")
    parser.add_argument("--backtranslations", type=Path)
    parser.add_argument("--skip-google", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    rank_corrections = reconcile_source_ranks(curriculum, args.corpus)
    draft_path = args.output / "reviewed_curriculum.json"
    draft_path.write_text(json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8")
    trace = {
        "generator_model": curriculum.get("model"),
        "repair_model": args.repair_model,
        "deterministic_rank_corrections": rank_corrections,
    }

    first_report = quality.verify(draft_path, args.corpus, args.backtranslations, False)
    repaired = []
    if args.repair_model:
        if args.repair_model == curriculum.get("model"):
            raise ValueError("Repair model must be independent from the generator model")
        repaired, usage = repair_rows(
            curriculum, first_report, args.repair_model, os.environ["OPENAI_API_KEY"]
        )
        curriculum = apply_repairs(curriculum, repaired, args.corpus)
        draft_path.write_text(
            json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        trace["repair_usage"] = usage
        trace["repaired_rows"] = len(repaired)

        residual_report = quality.verify(draft_path, args.corpus, None, False)
        residual_repairs, residual_usage = repair_rows(
            curriculum,
            residual_report,
            args.repair_model,
            os.environ["OPENAI_API_KEY"],
            errors_only=True,
        )
        if residual_repairs:
            curriculum = apply_repairs(curriculum, residual_repairs, args.corpus)
            draft_path.write_text(
                json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            trace["residual_repair_usage"] = residual_usage
            trace["residual_repaired_rows"] = len(residual_repairs)

    backtranslations_path = args.backtranslations
    evidence = (
        json.loads(backtranslations_path.read_text(encoding="utf-8"))
        if backtranslations_path
        else {"provider": None, "rows": []}
    )
    if backtranslations_path is None and not args.skip_google:
        if not os.environ.get("GOOGLE_TRANSLATE_API_KEY"):
            blocked = quality.verify(draft_path, args.corpus, None, True)
            quality.write_outputs(blocked, args.output)
            trace["approved"] = False
            trace["blocker"] = "GOOGLE_TRANSLATE_API_KEY is not configured"
            trace["final_summary"] = blocked["summary"]
            (args.output / "review_trace.json").write_text(
                json.dumps(trace, indent=2), encoding="utf-8"
            )
            raise ValueError("GOOGLE_TRANSLATE_API_KEY is not configured")
        evidence, google_usage = build_backtranslations(
            curriculum, os.environ["GOOGLE_TRANSLATE_API_KEY"]
        )
        backtranslations_path = args.output / "independent_backtranslations.json"
        backtranslations_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        trace["google_usage"] = google_usage

    # A second, independent-evidence repair pass touches only conflicts found after
    # back-translation, then refreshes evidence only for changed rows.
    if args.repair_model and backtranslations_path:
        independent_report = quality.verify(draft_path, args.corpus, backtranslations_path, True)
        second_repairs, second_usage = repair_rows(
            curriculum,
            independent_report,
            args.repair_model,
            os.environ["OPENAI_API_KEY"],
            {
                "backtranslation_conflict",
                "backtranslation_low_agreement",
                "backtranslated_word_conflict",
            },
        )
        if second_repairs:
            curriculum = apply_repairs(curriculum, second_repairs, args.corpus)
            draft_path.write_text(
                json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            trace["independent_repair_usage"] = second_usage
            trace["independent_repaired_rows"] = len(second_repairs)
            if not args.skip_google and args.backtranslations is None:
                changed = {(row["language"], row["id"]) for row in second_repairs}
                refreshed, refresh_usage = build_backtranslations(
                    curriculum, os.environ["GOOGLE_TRANSLATE_API_KEY"], changed
                )
                evidence = merge_backtranslations(evidence, refreshed)
                backtranslations_path.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                trace["google_refresh_usage"] = refresh_usage

    final_report = quality.verify(draft_path, args.corpus, backtranslations_path, True)
    quality.write_outputs(final_report, args.output)
    trace["approved"] = final_report["approved"]
    trace["final_summary"] = final_report["summary"]
    (args.output / "review_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(json.dumps(trace, indent=2))
    if not final_report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
