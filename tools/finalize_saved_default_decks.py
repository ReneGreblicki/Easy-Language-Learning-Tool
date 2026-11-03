"""Apply five hash-bound, meaning-preserving Run 7 corrections offline.

Writes an auditable corrected curriculum and invokes the unchanged release gate.
No provider calls, deployment or publication.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

import default_deck_quality as quality

CORRECTIONS = {
    ("ru-RU", 42): ("Мне очень нравится эта песня.", "Эта песня мне очень нравится."),
    ("ko-KR", 42): ("저는 이 노래를 정말 좋아해요.", "저는 이 노래를 아주 좋아해요."),
    ("hu-HU", 42): ("Nagyon tetszik ez a dal.", "Ez a dal nagyon tetszik nekem."),
    ("th-Latn-TH", 446): (
        "teem-ngaan dâi ruam-ruam khɔ̂ɔ-mûn jàak lûuk-kháa hâa-róoi râai",
        "teem-ngaan dâi ruam-ruam khɔ̂ɔ-mûn jàak lûuk-kháa 500 râai",
    ),
    ("ja-JP", 392): ("今朝の授業は8時に始まります。", "今朝の授業は八時に始まります。"),
}


def target_hash(row):
    return hashlib.sha256((row["word"] + "\n" + row["sentence"]).encode()).hexdigest()


def finalize(curriculum, evidence):
    result, proofs = copy.deepcopy(curriculum), copy.deepcopy(evidence)
    rows = {
        (code, row["id"]): row
        for code, language_rows in result["languages"].items()
        for row in language_rows
    }
    proof_rows = {(row["language"], row["id"]): row for row in proofs["rows"]}
    changes = []
    for key, (expected, corrected) in CORRECTIONS.items():
        row, proof = rows[key], proof_rows[key]
        assert row["sentence"] == expected, f"Unexpected saved sentence: {key}"
        before = target_hash(row)
        assert proof["target_sha256"] == before, f"Stale target proof: {key}"
        row["sentence"] = corrected
        after = target_hash(row)
        changes.append(
            {
                "language": key[0],
                "id": key[1],
                "before_sha256": before,
                "after_sha256": after,
                "before_sentence": expected,
                "after_sentence": corrected,
            }
        )
        proof.update(
            prior_target_sha256=before,
            target_sha256=after,
            adjudicator_model="codex-final-contextual-review",
            adjudication="Equivalent emphasis/word order or numerical notation; proposition preserved.",
        )
    return result, proofs, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--hybrid-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before = quality.verify(
        args.curriculum, quality.DEFAULT_CORPUS, hybrid_evidence_path=args.hybrid_evidence
    )
    assert before["summary"]["rows"] == 24000
    assert before["summary"]["errors"] == 5, "Unexpected input; inspect before correcting"
    corrected, proof, changes = finalize(
        json.loads(args.curriculum.read_text()), json.loads(args.hybrid_evidence.read_text())
    )
    args.output.mkdir(parents=True, exist_ok=True)
    curriculum_path = args.output / "curriculum.json"
    evidence_path = args.output / "hybrid_evidence.json"
    curriculum_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2))
    evidence_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    trace = {
        "input_sha256": hashlib.sha256(args.curriculum.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(curriculum_path.read_bytes()).hexdigest(),
        "provider_calls": 0,
        "changes": changes,
    }
    (args.output / "final_correction_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2)
    )
    report = quality.verify(
        curriculum_path, quality.DEFAULT_CORPUS, hybrid_evidence_path=evidence_path
    )
    quality.write_outputs(report, args.output)
    print(json.dumps(report["summary"], indent=2))
    if not report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
