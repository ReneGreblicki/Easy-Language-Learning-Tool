"""Blindly compare generated default-deck pilots; never publish content."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

SCORE_FIELDS = ("meaning", "naturalness", "headword", "level", "script", "format")
WEIGHTS = {
    "meaning": 35,
    "naturalness": 25,
    "headword": 15,
    "level": 10,
    "script": 10,
    "format": 5,
}
KNOWN_REGRESSIONS = {
    ("fr-FR", 406): "matter/be important, not importer",
    ("ml-IN", 708): "iron clothing, not sit",
    ("tr-TR", 1): "do not leave English 'the' as the target",
    ("zh-CN", 2): "use a pedagogically useful infinitive construction",
    ("ja-JP", 2): "use a natural Japanese infinitive/desire construction",
    ("ko-KR", 2): "use a natural Korean desire construction",
}


def parse_inputs(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        model, separator, path = value.partition("=")
        if not separator or not model or not path:
            raise ValueError("Each --input must use MODEL=CURRICULUM.json")
        result[model] = Path(path)
    if len(result) != 3:
        raise ValueError("Exactly three model curricula are required")
    return result


def blind_order(language: str, concept_id: int, models: list[str]) -> list[str]:
    return sorted(
        models,
        key=lambda model: hashlib.sha256(
            f"default-deck-eval-v1:{language}:{concept_id}:{model}".encode()
        ).hexdigest(),
    )


def weighted_score(row: dict) -> float:
    return sum(row[field] * WEIGHTS[field] for field in SCORE_FIELDS) / 5


def evaluation_schema() -> dict:
    properties = {
        "concept_id": {"type": "integer"},
        "label": {"type": "string", "enum": ["A", "B", "C"]},
        **{field: {"type": "integer", "minimum": 1, "maximum": 5} for field in SCORE_FIELDS},
        "fatal": {"type": "boolean"},
        "issue": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["evaluations"],
        "properties": {
            "evaluations": {
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


def judge_language(
    language: str,
    candidates: list[dict],
    model: str,
    reasoning_effort: str,
) -> tuple[list[dict], dict[str, int]]:
    instruction = (
        "Act as a strict multilingual curriculum evaluator. The model identities are hidden. "
        "Score every candidate independently from 1 (unacceptable) to 5 (excellent): meaning "
        "preservation; natural adult-neutral target-language sentence; usefulness and correctness "
        "of the study headword/construction; CEFR-level fit; correct script/romanization; and "
        "format/completeness. Treat literal calques, wrong senses, untranslated English labels, "
        "unnatural constructions, misleading dictionary forms, and changed propositions as serious. "
        "Mark fatal=true for a wrong meaning, wrong language/script, unusable headword, or materially "
        "ungrammatical sentence. For function words without direct equivalents, accept a concise, "
        "accurate pedagogical construction; do not reward a vague placeholder. For Thai Paiboon, "
        "require readable tone-marked romanization and no Thai characters. Return exactly one "
        "evaluation for every supplied concept_id and label. Keep issue empty when no material issue "
        "exists; otherwise state the problem briefly in English. Target language: " + language + "."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(candidates, ensure_ascii=False)},
        ],
        "reasoning_effort": reasoning_effort,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "blind_curriculum_evaluation",
                "strict": True,
                "schema": evaluation_schema(),
            },
        },
    }
    expected = {(row["concept_id"], row["label"]) for row in candidates}
    for attempt in range(5):
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = json.load(response)
            rows = json.loads(payload["choices"][0]["message"]["content"])["evaluations"]
            actual = {(row["concept_id"], row["label"]) for row in rows}
            if actual != expected or len(rows) != len(expected):
                raise ValueError("Judge omitted or duplicated candidates")
            usage = payload.get("usage", {})
            return rows, {
                "requests": 1,
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            }
        except (KeyError, OSError, ValueError) as error:
            if attempt == 4:
                raise
            body["messages"].append(
                {
                    "role": "user",
                    "content": f"The prior evaluation failed validation: {error}. Return all rows.",
                }
            )
            if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                try:
                    delay = max(10.0, float(error.headers.get("Retry-After", 0)))
                except (TypeError, ValueError):
                    delay = 10.0 * (attempt + 1)
            else:
                delay = float(2**attempt)
            time.sleep(delay)
    raise AssertionError("unreachable")


def build_candidates(
    curricula: dict[str, dict], language: str
) -> tuple[list[dict], dict[tuple[int, str], str]]:
    models = list(curricula)
    candidate_rows = []
    key = {}
    for concept_id in sorted(row["id"] for row in curricula[models[0]]["languages"][language]):
        order = blind_order(language, concept_id, models)
        for index, model in enumerate(order):
            label = chr(ord("A") + index)
            data = curricula[model]
            target = next(row for row in data["languages"][language] if row["id"] == concept_id)
            source_code = "th-Thai-TH" if language == "th-Latn-TH" else "en-US"
            source = next(row for row in data["languages"][source_code] if row["id"] == concept_id)
            candidate_rows.append(
                {
                    "concept_id": concept_id,
                    "label": label,
                    "level": target["level"],
                    "source_word": source["word"],
                    "source_sentence": source["sentence"],
                    "expected_sense_in_english": target["sense"],
                    "target_word": target["word"],
                    "target_sentence": target["sentence"],
                }
            )
            key[(concept_id, label)] = model
    return candidate_rows, key


def summarize(evaluations: list[dict], curricula: dict[str, dict]) -> dict:
    by_model = defaultdict(list)
    score_by_concept = defaultdict(list)
    for row in evaluations:
        by_model[row["model"]].append(row)
        score_by_concept[(row["language"], row["concept_id"])].append(row)
    summary = {}
    for model, rows in by_model.items():
        wins = 0.0
        for candidates in score_by_concept.values():
            best = max(weighted_score(row) for row in candidates)
            winners = [row for row in candidates if weighted_score(row) == best]
            if any(row["model"] == model for row in winners):
                wins += 1 / len(winners)
        source = curricula[model]
        summary[model] = {
            "rows": len(rows),
            "quality_score": round(statistics.fmean(weighted_score(row) for row in rows), 3),
            "fatal_errors": sum(row["fatal"] for row in rows),
            "wins": round(wins, 3),
            **{
                f"mean_{field}": round(statistics.fmean(row[field] for row in rows), 3)
                for field in SCORE_FIELDS
            },
            "generation_usage": source.get("api_usage", {}),
            "generation_elapsed_seconds": source.get("elapsed_seconds"),
            "reasoning_effort": source.get("reasoning_effort"),
        }
    return summary


def write_blind_pack(
    path: Path,
    candidates: list[dict],
    language: str,
) -> None:
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as stream:
        fieldnames = [
            "language",
            *candidates[0],
            "reviewer",
            "meaning_1_5",
            "naturalness_1_5",
            "headword_1_5",
            "level_1_5",
            "script_1_5",
            "fatal",
            "notes",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in candidates:
            writer.writerow({"language": language, **row})


def evaluate(
    input_paths: dict[str, Path],
    output: Path,
    judge_model: str,
    reasoning_effort: str,
) -> dict:
    curricula = {
        model: json.loads(path.read_text(encoding="utf-8")) for model, path in input_paths.items()
    }
    language_sets = {tuple(data["languages"]) for data in curricula.values()}
    if len(language_sets) != 1:
        raise ValueError("Model curricula contain different language sets")
    for data in curricula.values():
        if not data.get("pilot"):
            raise ValueError("Only pilot curricula may be evaluated by this workflow")

    output.mkdir(parents=True, exist_ok=True)
    blind_path = output / "blind_review.csv"
    blind_path.unlink(missing_ok=True)
    key_output = {}
    judged = []
    judge_usage = defaultdict(int)
    for language in next(iter(language_sets)):
        candidates, key = build_candidates(curricula, language)
        write_blind_pack(blind_path, candidates, language)
        key_output[language] = {
            f"{concept_id}:{label}": model for (concept_id, label), model in key.items()
        }
        rows, usage = judge_language(language, candidates, judge_model, reasoning_effort)
        for field, value in usage.items():
            judge_usage[field] += value
        for row in rows:
            row["language"] = language
            row["model"] = key[(row["concept_id"], row["label"])]
            judged.append(row)

    result = {
        "judge_model": judge_model,
        "judge_reasoning_effort": reasoning_effort,
        "judge_usage": dict(judge_usage),
        "rubric_weights": WEIGHTS,
        "summary": summarize(judged, curricula),
        "known_regressions": [
            {
                "language": language,
                "concept_id": concept_id,
                "expected": expected,
                "results": [
                    row
                    for row in judged
                    if row["language"] == language and row["concept_id"] == concept_id
                ],
            }
            for (language, concept_id), expected in KNOWN_REGRESSIONS.items()
        ],
        "evaluations": judged,
    }
    (output / "evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "review_key.json").write_text(
        json.dumps(key_output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Default-deck model evaluation",
        "",
        "Automated blind evaluation only. Native-language approval remains required.",
        "",
        "| Model | Quality / 100 | Fatal rows | Wins | Generation tokens | Seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, row in sorted(
        result["summary"].items(), key=lambda item: item[1]["quality_score"], reverse=True
    ):
        lines.append(
            f"| {model} | {row['quality_score']:.3f} | {row['fatal_errors']} | "
            f"{row['wins']:.3f} | {row['generation_usage'].get('total_tokens', 0)} | "
            f"{row['generation_elapsed_seconds']} |"
        )
    lines.extend(["", "## Known-regression rows", ""])
    for check in result["known_regressions"]:
        lines.append(f"### {check['language']} concept {check['concept_id']}: {check['expected']}")
        for row in sorted(check["results"], key=lambda value: value["model"]):
            lines.append(
                f"- **{row['model']}** — {weighted_score(row):.1f}/100; "
                f"fatal={str(row['fatal']).lower()}; {row['issue'] or 'no material issue reported'}"
            )
        lines.append("")
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--judge-model", default="gpt-6-astra")
    parser.add_argument("--reasoning-effort", default="high")
    args = parser.parse_args()
    evaluate(parse_inputs(args.input), args.output, args.judge_model, args.reasoning_effort)


if __name__ == "__main__":
    main()
