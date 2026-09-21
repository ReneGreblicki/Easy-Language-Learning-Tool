import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/build_default_decks.py"
spec = importlib.util.spec_from_file_location("default_curriculum", SCRIPT)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_source_and_identity():
    source = builder.frequency_data()
    assert len(source["en-US"]) == 5000
    assert len(builder.LANGUAGES) == 24
    catalog = (SCRIPT.parents[1] / "android_app/lib/data/default_catalog.dart").read_text()
    assert builder.stable_id("default:German:A1") in catalog
    assert builder.stable_id("default-card:de-DE:1") != builder.stable_id("default-card:fr-FR:1")


def test_reject_duplicate_concepts():
    row = {"id": 1, "word": "a", "sentence": "A cat sleeps.", "sense": "article"}
    with pytest.raises(ValueError, match="duplicated"):
        builder.validate_rows([row, row], [{"id": 1}, {"id": 2}])


def test_publication_rejects_pilot_and_stale_review(tmp_path):
    curriculum = tmp_path / "curriculum.json"
    review = tmp_path / "review.json"
    curriculum.write_text(json.dumps({"pilot": True, "languages": {}}))
    review.write_text(
        json.dumps(
            {
                "approved": True,
                "reviewer": "test",
                "sha256": hashlib.sha256(curriculum.read_bytes()).hexdigest(),
            }
        )
    )
    with pytest.raises(ValueError, match="complete"):
        builder.publication_sql(curriculum, review, 1)
    curriculum.write_text(json.dumps({"pilot": False, "languages": {}}))
    with pytest.raises(ValueError, match="exact"):
        builder.publication_sql(curriculum, review, 1)


def test_translation_checks_reject_copied_headwords_and_thai_script():
    tasks = [{"id": i, "word": "the"} for i in range(5)]
    copied = [{"id": i, "word": "the", "sentence": "Die Katze schläft."} for i in range(5)]
    with pytest.raises(ValueError, match="not translated"):
        builder.validate_language(copied, tasks, "German")
    with pytest.raises(ValueError, match="script found|tone marks"):
        builder.validate_language(
            [{"id": 0, "word": "แมว", "sentence": "maaeo"}], tasks, "Thai (Paiboon romanization)"
        )


def test_translation_checks_reject_changed_english_sense():
    tasks = [{"id": index, "word": "word", "sense": "the intended meaning"} for index in range(5)]
    rows = [
        {
            "id": index,
            "word": f"Wort{index}",
            "sentence": f"Wort{index} steht hier.",
            "sense": "a different meaning" if index == 3 else "the intended meaning",
        }
        for index in range(5)
    ]
    with pytest.raises(ValueError, match="sense changed"):
        builder.validate_language(rows, tasks, "German")


def test_romanization_requires_tones_and_native_target_must_be_used():
    tasks = [{"id": 1, "word": "ที่"}]
    with pytest.raises(ValueError, match="tone marks"):
        builder.validate_language(
            [{"id": 1, "word": "thi", "sentence": "chan pai thi suan"}],
            tasks,
            "Thai (Paiboon romanization)",
        )
    with pytest.raises(ValueError, match="absent"):
        builder.validate_language(
            [{"id": 1, "word": "ที่", "sentence": "สุนัขกำลังเห่า"}], tasks, "Thai (Thai script)"
        )
