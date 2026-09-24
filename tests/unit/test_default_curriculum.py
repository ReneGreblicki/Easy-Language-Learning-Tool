import hashlib
import importlib.util
import io
import json
import urllib.error
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


def test_reasoning_models_do_not_receive_temperature():
    assert builder.generation_options("gpt-5.6-luna", "high", 0.2) == {"reasoning_effort": "high"}
    assert builder.generation_options("gpt-4.1", None, 0.2) == {"temperature": 0.2}


def test_rate_limit_retry_respects_server_delay(monkeypatch):
    monkeypatch.setattr(builder.random, "uniform", lambda _low, _high: 0)
    error = urllib.error.HTTPError(
        "https://api.openai.com", 429, "rate limited", {"Retry-After": "17"}, None
    )
    assert builder.retry_delay(error, 0) == 17
    assert (
        builder.retry_delay(
            urllib.error.HTTPError("https://api.openai.com", 429, "rate limited", {}, None), 2
        )
        == 40
    )
    assert builder.request_timeout("medium") == 300
    assert builder.request_timeout(None) == 120


def test_spend_limit_429_is_not_retried():
    body = io.BytesIO(
        json.dumps(
            {
                "error": {
                    "type": "insufficient_quota",
                    "code": "project_spend_limit_exceeded",
                    "message": "Project limit reached.",
                }
            }
        ).encode()
    )
    error = urllib.error.HTTPError("https://api.openai.com", 429, "rate limited", {}, body)
    details = builder.openai_error_details(error)
    assert details["code"] == "project_spend_limit_exceeded"
    assert not builder.retryable_http_error(error, details)


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


def test_romanization_requires_tones():
    tasks = [{"id": 1, "word": "ที่"}]
    with pytest.raises(ValueError, match="tone marks"):
        builder.validate_language(
            [{"id": 1, "word": "thi", "sentence": "chan pai thi suan"}],
            tasks,
            "Thai (Paiboon romanization)",
        )
