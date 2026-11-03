import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import finalize_saved_default_decks as finalizer


def saved_input():
    curriculum = {"languages": {}}
    proofs = {"rows": []}
    for (language, concept_id), (sentence, _) in finalizer.CORRECTIONS.items():
        row = {
            "id": concept_id,
            "word": "stable",
            "sentence": sentence,
            "sense": "stable sense",
            "level": "A1",
            "rank": 1,
        }
        curriculum["languages"].setdefault(language, []).append(row)
        proofs["rows"].append(
            {
                "language": language,
                "id": concept_id,
                "source_sha256": "source-proof",
                "target_sha256": finalizer.target_hash(row),
            }
        )
    return curriculum, proofs


def test_final_corrections_preserve_identity_source_and_input():
    curriculum, evidence = saved_input()
    original = copy.deepcopy((curriculum, evidence))
    corrected, proofs, changes = finalizer.finalize(curriculum, evidence)
    assert (curriculum, evidence) == original
    assert len(changes) == 5
    for code, rows in corrected["languages"].items():
        for before, after in zip(curriculum["languages"][code], rows, strict=True):
            assert {k: v for k, v in before.items() if k != "sentence"} == {
                k: v for k, v in after.items() if k != "sentence"
            }
    assert all(p["source_sha256"] == "source-proof" for p in proofs["rows"])


def test_final_corrections_fail_closed_on_stale_evidence():
    curriculum, evidence = saved_input()
    evidence["rows"][0]["target_sha256"] = "stale"
    with pytest.raises(AssertionError, match="Stale target proof"):
        finalizer.finalize(curriculum, evidence)
