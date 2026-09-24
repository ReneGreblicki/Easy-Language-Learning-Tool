"""Cost-gated automated review, repair, and hybrid-evidence checks.

The adjudicator sees only rows flagged by deterministic checks. The preferred pipeline
uses content-bound Google-draft/GPT-edit evidence; legacy back-translation evidence is
still accepted. Final release approval is delegated to ``default_deck_quality.py``,
which has no network code.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import default_deck_quality as quality

try:
    from api_cost_guard import CostBudget
except ModuleNotFoundError:  # Imported directly by unit tests from the repository root.
    from tools.api_cost_guard import CostBudget

ROOT = Path(__file__).resolve().parents[1]
MAX_REPAIR_COMPLETION_TOKENS = 4096

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
    body = json.dumps({"q": values, "target": target, "format": "text"}).encode()
    request = urllib.request.Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=body,
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
    )
    # Do not automatically repeat a potentially billable translation request.
    payload = request_json(request, attempts=1)
    translations = payload["data"]["translations"]
    if len(translations) != len(values):
        raise ValueError("Google Translation returned an incomplete batch")
    return [html.unescape(row["translatedText"]) for row in translations]


def build_backtranslations(
    curriculum: dict,
    api_key: str,
    only: set[tuple[str, int]] | None = None,
    max_characters: int = 100_000,
    max_requests: int = 48,
    checkpoint_dir: Path | None = None,
) -> tuple[dict, dict]:
    planned: list[tuple[str, list[dict], list[str]]] = []
    for code, rows in curriculum["languages"].items():
        if code == "en-US":
            continue
        selected = [row for row in rows if only is None or (code, row["id"]) in only]
        for start in range(0, len(selected), 50):
            batch = selected[start : start + 50]
            values = [value for row in batch for value in (row["word"], row["sentence"])]
            planned.append((code, batch, values))
    planned_characters = sum(len(value) for _, _, values in planned for value in values)
    if planned_characters > max_characters or len(planned) > max_requests:
        raise RuntimeError(
            "Google Translation hard cap blocks this run before any request: "
            f"characters={planned_characters}/{max_characters}, "
            f"requests={len(planned)}/{max_requests}"
        )

    if checkpoint_dir:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output = []
    characters = 0
    paid_requests = 0
    cached_requests = 0
    for code, batch, values in planned:
        batch_characters = sum(len(value) for value in values)
        characters += batch_characters
        digest = hashlib.sha256(
            json.dumps([code, values, "en"], ensure_ascii=False).encode()
        ).hexdigest()[:24]
        checkpoint = checkpoint_dir / f"google-{code}-{digest}.json" if checkpoint_dir else None
        if checkpoint and checkpoint.exists():
            translated = json.loads(checkpoint.read_text(encoding="utf-8"))
            cached_requests += 1
        else:
            translated = translate_google(values, "en", api_key)
            paid_requests += 1
            if checkpoint:
                checkpoint.write_text(
                    json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8"
                )
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
        "requests": paid_requests,
        "cached_requests": cached_requests,
        "characters": characters,
        "rows": len(output),
        "max_characters": max_characters,
        "max_requests": max_requests,
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
    budget: CostBudget | None = None,
    checkpoint_dir: Path | None = None,
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
    if checkpoint_dir:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(candidates), 24):
        batch = candidates[start : start + 24]
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_completion_tokens": MAX_REPAIR_COMPLETION_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "corrected_rows",
                    "strict": True,
                    "schema": repair_schema(),
                },
            },
        }
        encoded_body = json.dumps(body, ensure_ascii=False).encode()
        digest = hashlib.sha256(
            json.dumps([model, batch], ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:24]
        checkpoint = checkpoint_dir / f"repair-{model}-{digest}.json" if checkpoint_dir else None
        if checkpoint and checkpoint.exists():
            rows = json.loads(checkpoint.read_text(encoding="utf-8"))
            usage["cached_requests"] += 1
        else:
            if budget:
                budget.preflight(model, encoded_body, MAX_REPAIR_COMPLETION_TOKENS)
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=encoded_body,
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            )
            payload = request_json(request)
            rows = json.loads(payload["choices"][0]["message"]["content"])["rows"]
            provider_usage = payload.get("usage", {})
            usage["requests"] += 1
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                usage[key] += int(provider_usage.get(key, 0))
            if budget:
                usage["estimated_cost_usd"] += budget.record(model, provider_usage)
        expected = {(row["language"], row["id"]) for row in batch}
        actual = {(row["language"], row["id"]) for row in rows}
        if actual != expected or len(rows) != len(expected):
            raise ValueError("Repair model omitted, duplicated, or added rows")
        if checkpoint and not checkpoint.exists():
            checkpoint.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        repaired.extend(rows)
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


def update_hybrid_evidence(
    evidence: dict, curriculum: dict, repaired: list[dict], adjudicator_model: str
) -> dict:
    """Bind repaired rows to the existing Google-draft provenance chain."""
    changed = {(row["language"], row["id"]): row for row in repaired}
    by_key = {(row["language"], row["id"]): row for row in evidence.get("rows", [])}
    curriculum_rows = {
        (code, row["id"]): row for code, rows in curriculum["languages"].items() for row in rows
    }
    for key, repair in changed.items():
        row = curriculum_rows[key]
        proof = by_key.get(key)
        if proof is None:
            raise ValueError(f"Hybrid evidence is missing for repaired row {key}")
        proof["target_sha256"] = hashlib.sha256(
            (row["word"] + "\n" + row["sentence"]).encode()
        ).hexdigest()
        proof["adjudicator_model"] = adjudicator_model
        proof["adjudication"] = repair.get("explanation", "corrected")
    evidence["rows"] = list(by_key.values())
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=quality.DEFAULT_CORPUS)
    parser.add_argument("--repair-model")
    parser.add_argument(
        "--escalation-model",
        help="Independent higher-cost model used only for residual deterministic errors.",
    )
    parser.add_argument("--backtranslations", type=Path)
    parser.add_argument("--hybrid-evidence", type=Path)
    parser.add_argument("--skip-google", action="store_true")
    parser.add_argument("--max-openai-cost-usd", type=float, default=1.0)
    parser.add_argument("--max-google-characters", type=int, default=100_000)
    parser.add_argument("--max-google-requests", type=int, default=48)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    rank_corrections = reconcile_source_ranks(curriculum, args.corpus)
    draft_path = args.output / "reviewed_curriculum.json"
    draft_path.write_text(json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8")
    trace = {
        "generator_model": curriculum.get("model"),
        "repair_model": args.repair_model,
        "escalation_model": args.escalation_model,
        "max_openai_cost_usd": args.max_openai_cost_usd,
        "max_google_characters": args.max_google_characters,
        "max_google_requests": args.max_google_requests,
        "deterministic_rank_corrections": rank_corrections,
    }
    budget = CostBudget(args.max_openai_cost_usd)
    checkpoint_dir = args.output / "checkpoints"
    trace_path = args.output / "review_trace.json"
    hybrid_evidence = (
        json.loads(args.hybrid_evidence.read_text(encoding="utf-8"))
        if args.hybrid_evidence
        else None
    )
    hybrid_evidence_path = args.output / "hybrid_evidence.json" if hybrid_evidence else None
    if hybrid_evidence_path:
        hybrid_evidence_path.write_text(
            json.dumps(hybrid_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def persist_trace() -> None:
        trace["openai_estimated_cost_usd"] = round(budget.spent_usd, 8)
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    persist_trace()

    first_report = quality.verify(
        draft_path, args.corpus, args.backtranslations, False, hybrid_evidence_path
    )
    repaired = []
    if args.repair_model:
        if args.repair_model == curriculum.get("model"):
            raise ValueError("Repair model must be independent from the generator model")
        repaired, usage = repair_rows(
            curriculum,
            first_report,
            args.repair_model,
            os.environ["OPENAI_API_KEY"],
            errors_only=hybrid_evidence is not None,
            budget=budget,
            checkpoint_dir=checkpoint_dir,
        )
        curriculum = apply_repairs(curriculum, repaired, args.corpus)
        if hybrid_evidence is not None:
            hybrid_evidence = update_hybrid_evidence(
                hybrid_evidence, curriculum, repaired, args.repair_model
            )
            hybrid_evidence_path.write_text(
                json.dumps(hybrid_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        draft_path.write_text(
            json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        trace["repair_usage"] = usage
        trace["repaired_rows"] = len(repaired)
        persist_trace()

        residual_report = quality.verify(draft_path, args.corpus, None, False, hybrid_evidence_path)
        residual_model = args.escalation_model or args.repair_model
        residual_repairs, residual_usage = repair_rows(
            curriculum,
            residual_report,
            residual_model,
            os.environ["OPENAI_API_KEY"],
            errors_only=True,
            budget=budget,
            checkpoint_dir=checkpoint_dir,
        )
        if residual_repairs:
            curriculum = apply_repairs(curriculum, residual_repairs, args.corpus)
            if hybrid_evidence is not None:
                hybrid_evidence = update_hybrid_evidence(
                    hybrid_evidence, curriculum, residual_repairs, residual_model
                )
                hybrid_evidence_path.write_text(
                    json.dumps(hybrid_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            draft_path.write_text(
                json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            trace["residual_repair_usage"] = residual_usage
            trace["residual_repaired_rows"] = len(residual_repairs)
            trace["residual_repair_model"] = residual_model
            persist_trace()

    backtranslations_path = args.backtranslations
    evidence = (
        json.loads(backtranslations_path.read_text(encoding="utf-8"))
        if backtranslations_path
        else {"provider": None, "rows": []}
    )
    if backtranslations_path is None and hybrid_evidence is None and not args.skip_google:
        if not os.environ.get("GOOGLE_TRANSLATE_API_KEY"):
            blocked = quality.verify(draft_path, args.corpus, None, True)
            quality.write_outputs(blocked, args.output)
            trace["approved"] = False
            trace["blocker"] = "GOOGLE_TRANSLATE_API_KEY is not configured"
            trace["final_summary"] = blocked["summary"]
            persist_trace()
            raise ValueError("GOOGLE_TRANSLATE_API_KEY is not configured")
        evidence, google_usage = build_backtranslations(
            curriculum,
            os.environ["GOOGLE_TRANSLATE_API_KEY"],
            max_characters=args.max_google_characters,
            max_requests=args.max_google_requests,
            checkpoint_dir=checkpoint_dir,
        )
        backtranslations_path = args.output / "independent_backtranslations.json"
        backtranslations_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        trace["google_usage"] = google_usage
        persist_trace()

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
            budget=budget,
            checkpoint_dir=checkpoint_dir,
        )
        if second_repairs:
            curriculum = apply_repairs(curriculum, second_repairs, args.corpus)
            draft_path.write_text(
                json.dumps(curriculum, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            trace["independent_repair_usage"] = second_usage
            trace["independent_repaired_rows"] = len(second_repairs)
            persist_trace()
            if not args.skip_google and args.backtranslations is None:
                changed = {(row["language"], row["id"]) for row in second_repairs}
                used_characters = int(trace["google_usage"]["characters"])
                used_requests = int(trace["google_usage"]["requests"])
                refreshed, refresh_usage = build_backtranslations(
                    curriculum,
                    os.environ["GOOGLE_TRANSLATE_API_KEY"],
                    changed,
                    max_characters=max(0, args.max_google_characters - used_characters),
                    max_requests=max(0, args.max_google_requests - used_requests),
                    checkpoint_dir=checkpoint_dir,
                )
                evidence = merge_backtranslations(evidence, refreshed)
                backtranslations_path.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                trace["google_refresh_usage"] = refresh_usage
                persist_trace()

    final_report = quality.verify(
        draft_path, args.corpus, backtranslations_path, True, hybrid_evidence_path
    )
    quality.write_outputs(final_report, args.output)
    trace["approved"] = final_report["approved"]
    trace["final_summary"] = final_report["summary"]
    persist_trace()
    print(json.dumps(trace, indent=2))
    if not final_report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
