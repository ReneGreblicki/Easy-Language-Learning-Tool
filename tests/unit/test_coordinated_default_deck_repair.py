import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import repair_coordinated_default_decks as repair


def test_contextual_correction_preserves_sentence_and_records_hash():
    row = {
        "id": 911,
        "word": "Australia",
        "sentence": "Przeprowadziła się do Australii.",
        "sense": "the country Australia",
        "level": "B1",
    }
    untouched = {"id": 12, "word": "zimno", "sentence": "Jest zimno.", "level": "A1"}
    curriculum = {"languages": {"pl-PL": [row, untouched]}}
    original = copy.deepcopy(curriculum)
    before = repair.target_hash(row)
    evidence = {
        "rows": [
            {
                "language": "pl-PL",
                "id": 911,
                "target_sha256": before,
                "source_sha256": "source-proof",
            }
        ]
    }
    changes = repair.apply_focused_corrections(curriculum, evidence)
    assert len(changes) == 1
    assert row["word"] == "do Australii"
    assert row["sentence"] == original["languages"]["pl-PL"][0]["sentence"]
    assert untouched == original["languages"]["pl-PL"][1]
    proof = evidence["rows"][0]
    assert proof["source_sha256"] == "source-proof"
    assert proof["prior_target_sha256"] == before
    assert proof["target_sha256"] == repair.target_hash(row)


def test_contextual_correction_rejects_stale_input_proof():
    curriculum = {
        "languages": {"pl-PL": [{"id": 911, "word": "Australia", "sentence": "do Australii"}]}
    }
    evidence = {"rows": [{"language": "pl-PL", "id": 911, "target_sha256": "stale"}]}
    with pytest.raises(AssertionError, match="stale"):
        repair.apply_focused_corrections(curriculum, evidence)


def test_korean_written_month_preserves_numeric_value():
    row = {"id": 540, "word": "3월", "sentence": "3월은 2월보다 따뜻합니다."}
    evidence = {
        "rows": [{"language": "ko-KR", "id": 540, "target_sha256": repair.target_hash(row)}]
    }
    repair.apply_focused_corrections({"languages": {"ko-KR": [row]}}, evidence)
    assert row["word"] == "삼월"
    assert row["sentence"] == "삼월은 이월보다 따뜻합니다."
