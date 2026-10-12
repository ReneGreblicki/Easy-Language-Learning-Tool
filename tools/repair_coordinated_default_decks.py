"""Repair duplicate concepts across languages from a complete saved curriculum.

No full generation or publication. Paid work is limited to changed concept IDs;
Google provenance is refreshed and Paiboon follows the final native Thai source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import build_default_decks as builder
import default_deck_quality as quality
import review_default_deck_curriculum as review
from api_cost_guard import CostBudget

SOURCE_SENTENCES = {
    42: "I like this song a lot.",
    82: "I gave him the blue book.",
    156: "I am ready for school today.",
    385: "We're ready to go home now.",
    392: "The class starts at eight o'clock this morning.",
    522: "I am ready to leave for school because my bag is packed.",
    553: "The children are playing outside because the weather is warm today.",
    699: "Please wash your hands before dinner because they are dirty.",
}

# Contextual constructions retain proper nouns and valid cognates. This avoids
# replacing a correct local term merely to satisfy an English-equality heuristic.
HEADWORD_CORRECTIONS = {
    ("pl-PL", 911): "do Australii",
    ("sk-SK", 811): "v auguste",
    ("sk-SK", 959): "India má",
    ("hu-HU", 959): "Indiának",
    ("nb-NO", 705): "originalmaleriet",
    ("nb-NO", 763): "en god match",
    ("nb-NO", 936): "antirøykingskampanje",
    ("sv-SE", 541): "processen",
    ("sv-SE", 688): "en policy",
    ("sv-SE", 705): "originalmålningen",
    ("sv-SE", 757): "federala",
    ("ru-RU", 505): "Рокки II",
}
KOREAN_MONTHS = {
    "2월": "이월",
    "3월": "삼월",
    "4월": "사월",
    "6월": "유월",
    "8월": "팔월",
    "9월": "구월",
    "10월": "시월",
    "11월": "십일월",
}


def target_hash(row: dict) -> str:
    return hashlib.sha256((row["word"] + "\n" + row["sentence"]).encode()).hexdigest()


def apply_focused_corrections(curriculum: dict, evidence: dict) -> list[dict]:
    indexes = {
        code: {row["id"]: row for row in rows} for code, rows in curriculum["languages"].items()
    }
    proofs = {(row["language"], row["id"]): row for row in evidence["rows"]}
    changes = []
    for code, rows in indexes.items():
        for concept_id, row in rows.items():
            before = target_hash(row)
            replacement = HEADWORD_CORRECTIONS.get((code, concept_id))
            if replacement:
                row["word"] = replacement
            if code == "ko-KR":
                if concept_id == 505:
                    row["word"] = "록키 II"
                    row["sentence"] = row["sentence"].replace("2편", "II")
                for digits, spelled in KOREAN_MONTHS.items():
                    # Replace longest digit tokens first; 10월 is never 0월.
                    row["word"] = row["word"].replace(digits, spelled)
                    row["sentence"] = row["sentence"].replace(digits, spelled)
            if target_hash(row) != before:
                proof = proofs[(code, concept_id)]
                assert proof["target_sha256"] == before, "Input proof is stale"
                proof["prior_target_sha256"] = before
                proof["target_sha256"] = target_hash(row)
                proof["adjudicator_model"] = "codex-contextual-correction"
                proof["adjudication"] = (
                    "Contextual headword or equivalent written number; proposition preserved."
                )
                changes.append(
                    {
                        "language": code,
                        "id": concept_id,
                        "before_sha256": before,
                        "after_sha256": target_hash(row),
                    }
                )
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--hybrid-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-openai-cost-usd", type=float, default=1.0)
    parser.add_argument("--max-google-new-characters", type=int, default=100000)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    curriculum = json.loads(args.curriculum.read_text())
    evidence = json.loads(args.hybrid_evidence.read_text())
    languages = curriculum["languages"]
    assert len(languages) == 24
    assert all(
        len(rows) == 1000 and {r["id"] for r in rows} == set(range(1, 1001))
        for rows in languages.values()
    ), "Incomplete curriculum; no paid requests allowed"
    assert len(evidence["rows"]) == 23000
    before_report = quality.verify(
        args.curriculum, quality.DEFAULT_CORPUS, hybrid_evidence_path=args.hybrid_evidence
    )
    allowed = {
        "duplicate_sentences",
        "possible_untranslated_word",
        "number_drift",
        "missing_script",
        "missing_tone_marks",
        "stale_hybrid_evidence",
    }
    assert all(
        f["code"] in allowed for f in before_report["findings"] if f["severity"] == "error"
    ), "Unexpected input errors; no paid requests allowed"
    assert all(
        (f["language"], f["concept_id"]) == ("th-Latn-TH", 672)
        for f in before_report["findings"]
        if f["code"] == "stale_hybrid_evidence"
    )
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output / "checkpoints"
    checkpoint.mkdir(exist_ok=True)
    builder.ACTIVE_BUDGET = CostBudget(args.max_openai_cost_usd)
    builder.MAX_GOOGLE_NEW_CHARACTERS = args.max_google_new_characters
    indexes = {code: {r["id"]: r for r in rows} for code, rows in languages.items()}
    proofs = {(r["language"], r["id"]): r for r in evidence["rows"]}
    trace = {
        "source_concept_ids": sorted(SOURCE_SENTENCES),
        "refreshed_rows": [],
        "focused_corrections": apply_focused_corrections(curriculum, evidence),
    }
    for concept_id, sentence in SOURCE_SENTENCES.items():
        row = indexes["en-US"][concept_id]
        issues = builder.english_usage_issues(row["word"], sentence, row["sense"])
        assert not issues, issues
        row["sentence"] = sentence
    if args.plan_only:
        (args.output / "repair_plan.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2)
        )
        print(
            json.dumps(
                {
                    "concept_ids": sorted(SOURCE_SENTENCES),
                    "translation_cells": len(SOURCE_SENTENCES) * 23 + 3,
                    "focused_corrections": len(trace["focused_corrections"]),
                }
            )
        )
        return
    frequencies = builder.frequency_data()
    model = "gpt-4.1-mini"
    codes = [c for c in languages if c not in ("en-US", "th-Latn-TH")] + ["th-Latn-TH"]
    for code in codes:
        ids = set(SOURCE_SENTENCES)
        if code == "th-Latn-TH":
            # Also refresh the stale native-Thai dependency and the two rejected
            # Paiboon rows. Never rebind a stale source hash without retransliterating.
            ids.update((2, 446, 672))
        source = indexes["th-Thai-TH"] if code == "th-Latn-TH" else indexes["en-US"]
        tasks = [source[i] for i in sorted(ids)]
        digest = hashlib.sha256(
            json.dumps(
                ["coordinated-v1", model, code, tasks], sort_keys=True, ensure_ascii=False
            ).encode()
        ).hexdigest()[:24]
        cached = checkpoint / f"coordinated-{code}-{digest}.json"
        if code in builder.GOOGLE_TARGETS:
            drafts = builder.google_draft_rows(
                tasks, code, os.environ["GOOGLE_TRANSLATE_API_KEY"], checkpoint
            )
            enriched = [
                {
                    **task,
                    "ranked_target_candidates": builder.frequency_candidates(
                        draft["sentence"], frequencies[code]
                    ),
                }
                for task, draft in zip(tasks, drafts, strict=True)
            ]
            rows = (
                json.loads(cached.read_text())
                if cached.exists()
                else builder.review_rows(enriched, drafts, builder.LANGUAGES[code], model)
            )
        else:
            drafts = []
            rows = (
                json.loads(cached.read_text())
                if cached.exists()
                else builder.request_rows(tasks, builder.LANGUAGES[code], model)
            )
        builder.validate_rows(rows, tasks)
        builder.validate_language(rows, tasks, builder.LANGUAGES[code])
        cached.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        for position, (task, result) in enumerate(zip(tasks, rows, strict=True)):
            row = indexes[code][result["id"]]
            row.update(word=result["word"], sentence=result["sentence"], sense=task["sense"])
            if code == "ko-KR" and row["id"] == 392:
                row.update(word="여덟", sentence="수업은 오늘 아침 여덟 시에 시작해요.")
            if code == "th-Latn-TH" and row["id"] == 446:
                # The native row contains a literal 500. Paiboon may transliterate
                # its spoken form; retain the same value in the required digit format.
                row["sentence"] = row["sentence"].replace("hâa-rɔ́ɔi", "500")
            proofs[(code, row["id"])] = {
                "language": code,
                "id": row["id"],
                "editor_model": model,
                "draft_provider": "google-cloud-translation-v2"
                if drafts
                else "thai-script-specialized",
                "source_sha256": builder.source_row_hash(task),
                "target_sha256": target_hash(row),
                **({"google_draft_sentence": drafts[position]["sentence"]} if drafts else {}),
            }
            trace["refreshed_rows"].append({"language": code, "id": row["id"]})
        evidence["rows"] = list(proofs.values())
        review.reconcile_source_ranks(curriculum, quality.DEFAULT_CORPUS)
        (args.output / "reviewed_curriculum.json").write_text(
            json.dumps(curriculum, ensure_ascii=False, indent=2)
        )
        (args.output / "hybrid_evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2)
        )
        trace.update(openai_usage=builder.API_USAGE, google_usage=builder.GOOGLE_USAGE)
        (args.output / "coordinated_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2)
        )
    report = quality.verify(
        args.output / "reviewed_curriculum.json",
        quality.DEFAULT_CORPUS,
        hybrid_evidence_path=args.output / "hybrid_evidence.json",
    )
    quality.write_outputs(report, args.output)
    print(json.dumps(report["summary"], indent=2))
    if not report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
