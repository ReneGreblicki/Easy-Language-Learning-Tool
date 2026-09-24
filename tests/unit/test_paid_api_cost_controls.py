import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

import api_cost_guard as costs  # noqa: E402
import build_default_decks as builder  # noqa: E402
import review_default_deck_curriculum as review  # noqa: E402


def curriculum() -> dict:
    return {
        "languages": {
            "en-US": [{"id": 1, "word": "cat", "sentence": "The cat sleeps.", "sense": "animal"}],
            "es-ES": [{"id": 1, "word": "gato", "sentence": "El gato duerme.", "sense": "animal"}],
        }
    }


def test_cost_budget_blocks_expensive_request_before_dispatch():
    budget = costs.CostBudget(0.50)
    with pytest.raises(RuntimeError, match="before the next request"):
        budget.preflight("gpt-6-astra", b"{}", 16_000)


def test_hybrid_aggregate_cap_blocks_configuration_before_api_use(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "secret")
    with pytest.raises(ValueError, match=r"\$23 build budget"):
        builder.generate(
            tmp_path,
            True,
            ["es-ES"],
            "gpt-5.6-luna",
            max_cost_usd=4.0,
            pipeline="hybrid",
            max_google_characters=1_000_000,
        )


def test_google_character_cap_blocks_before_network(monkeypatch):
    called = False

    def unexpected(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(review, "translate_google", unexpected)
    with pytest.raises(RuntimeError, match="before any request"):
        review.build_backtranslations(curriculum(), "secret", max_characters=1)
    assert not called


def test_google_key_is_header_only_and_request_is_not_retried(monkeypatch):
    captured = {}

    def fake_request(request, attempts=4):
        captured["url"] = request.full_url
        captured["key"] = request.headers["X-goog-api-key"]
        captured["attempts"] = attempts
        captured["body"] = json.loads(request.data)
        return {"data": {"translations": [{"translatedText": "cat"}]}}

    monkeypatch.setattr(review, "request_json", fake_request)
    assert review.translate_google(["gato"], "en", "super-secret") == ["cat"]
    assert "super-secret" not in captured["url"]
    assert captured["key"] == "super-secret"
    assert captured["attempts"] == 1
    assert captured["body"]["q"] == ["gato"]


def test_google_checkpoint_prevents_duplicate_paid_call(tmp_path, monkeypatch):
    calls = 0

    def fake_translate(values, _target, _key):
        nonlocal calls
        calls += 1
        return ["cat", "the cat sleeps"]

    monkeypatch.setattr(review, "translate_google", fake_translate)
    first, usage = review.build_backtranslations(
        curriculum(), "secret", checkpoint_dir=tmp_path, max_characters=1_000
    )
    second, resumed_usage = review.build_backtranslations(
        curriculum(), "secret", checkpoint_dir=tmp_path, max_characters=1_000
    )
    assert first == second
    assert calls == 1
    assert usage["requests"] == 1
    assert resumed_usage["requests"] == 0
    assert resumed_usage["cached_requests"] == 1


def test_paid_workflows_are_manual_only_and_budgeted():
    root = Path(__file__).resolve().parents[2]
    pilot = (root / ".github/workflows/default-deck-pilot.yml").read_text()
    evaluation = (root / ".github/workflows/default-deck-model-evaluation.yml").read_text()
    assert "pull_request:" not in pilot
    assert "pull_request:" not in evaluation
    assert "paid-default-deck-workflows" in pilot
    assert "paid-default-deck-workflows" in evaluation
    assert "--pipeline hybrid" in pilot
    assert "--model gpt-5.6-luna" in pilot
    assert "--max-cost-usd 0.50" in pilot
    assert "--max-openai-cost-usd 0.50" in pilot
    assert "--max-google-characters 100000" in pilot
    assert "--hybrid-evidence default-deck-pilot/hybrid_evidence.json" in pilot
    assert "--repair-model gpt-4.1-mini" in pilot
    assert "--pipeline direct" in evaluation
    assert "--judge-model gpt-6-luna" in evaluation
    assert "gpt-6-astra" not in evaluation


def test_hybrid_repair_rebinds_content_evidence():
    evidence = {
        "pipeline": "google-draft-gpt-post-edit-v1",
        "rows": [
            {
                "language": "es-ES",
                "id": 1,
                "target_sha256": "old",
                "draft_provider": "google-cloud-translation-v2",
            }
        ],
    }
    data = curriculum()
    repaired = [
        {
            "language": "es-ES",
            "id": 1,
            "target_word": "gato",
            "target_sentence": "El gato está durmiendo.",
            "sense_in_english": "animal",
            "explanation": "Natural progressive form.",
        }
    ]
    data["languages"]["es-ES"][0]["sentence"] = "El gato está durmiendo."
    updated = review.update_hybrid_evidence(evidence, data, repaired, "gpt-4.1-mini")
    proof = updated["rows"][0]
    assert proof["target_sha256"] != "old"
    assert proof["adjudicator_model"] == "gpt-4.1-mini"
    assert proof["adjudication"] == "Natural progressive form."
