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
    assert builder.generation_options("gpt-5.6-luna", None, 0.2) == {}
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


def test_google_sentence_request_keeps_key_out_of_url(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(
                {"data": {"translations": [{"translatedText": "El gato duerme."}]}}
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["key"] = request.headers["X-goog-api-key"]
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr(builder.urllib.request, "urlopen", fake_urlopen)
    assert builder.translate_google_sentences(["The cat sleeps."], "es", "secret") == [
        "El gato duerme."
    ]
    assert "secret" not in captured["url"]
    assert captured["key"] == "secret"
    assert captured["body"]["source"] == "en"
    assert captured["timeout"] == 180


def test_frequency_candidates_use_ranked_corpus_order():
    corpus = [
        {"lemma": "gato", "rank": 10},
        {"lemma": "duerme", "rank": 20},
        {"lemma": "perro", "rank": 30},
    ]
    assert builder.frequency_candidates("El gato duerme.", corpus) == [
        {"lemma": "gato", "rank": 10},
        {"lemma": "duerme", "rank": 20},
    ]


def test_hybrid_generation_writes_content_bound_evidence(tmp_path, monkeypatch):
    frequencies = {
        "en-US": [
            {"rank": rank, "lemma": f"word{rank}", "source": "test"} for rank in range(1, 1001)
        ],
        "es-ES": [
            {"rank": rank, "lemma": f"palabra{rank}", "source": "test"} for rank in range(1, 1001)
        ],
    }

    def fake_request(tasks, _language, _model, _reasoning=None):
        return [
            {
                "id": task["id"],
                "word": task["word"],
                "sentence": f"English example {task['id']}.",
                "sense": f"sense {task['id']}",
            }
            for task in tasks
        ]

    def fake_google(tasks, _code, _key, _checkpoint):
        return [
            {
                "id": task["id"],
                "word": "draft",
                "sentence": f"Borrador {task['id']}.",
                "sense": task["sense"],
            }
            for task in tasks
        ]

    def fake_review(tasks, _drafts, _language, _model, _reasoning=None):
        return [
            {
                "id": task["id"],
                "word": f"palabra{task['id']}",
                "sentence": f"La palabra {task['id']} aparece aquí.",
                "sense": task["sense"],
            }
            for task in tasks
        ]

    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "secret")
    monkeypatch.setattr(builder, "frequency_data", lambda: frequencies)
    monkeypatch.setattr(builder, "request_rows", fake_request)
    monkeypatch.setattr(builder, "google_draft_rows", fake_google)
    monkeypatch.setattr(builder, "review_rows", fake_review)
    result = builder.generate(
        tmp_path,
        True,
        ["es-ES"],
        "gpt-5.6-luna",
        max_cost_usd=0.5,
        pipeline="hybrid",
        max_google_characters=100_000,
        max_google_requests=48,
    )
    evidence = json.loads((tmp_path / "hybrid_evidence.json").read_text())
    assert result["pipeline"] == "hybrid"
    assert len(evidence["rows"]) == 30
    assert all(row["draft_provider"] == "google-cloud-translation-v2" for row in evidence["rows"])



def test_romanization_repair_retries_only_invalid_rows(monkeypatch):
    tasks = [
        {
            "id": 1,
            "word": "แมว",
            "sentence": "แมวนอนที่นี่",
            "sense": "cat",
            "level": "A1",
        },
        {
            "id": 2,
            "word": "สุนัข",
            "sentence": "สุนัขอยู่ที่นี่",
            "sense": "dog",
            "level": "A1",
        },
    ]
    valid_row = {
        "id": 1,
        "word": "mɛɛo",
        "sentence": "Mɛɛo nɔɔn thîi-nîi.",
        "sense": "cat",
    }
    invalid_row = {
        "id": 2,
        "word": "สุนัข",
        "sentence": "สุนัข yùu thîi-nîi.",
        "sense": "dog",
    }
    calls = []

    def fake_repair(repair_tasks, _failed, _model, _reasoning=None):
        calls.append([task["id"] for task in repair_tasks])
        return [
            {
                "id": 2,
                "word": "sù-nák",
                "sentence": "Sù-nák yùu thîi-nîi.",
                "sense": "dog",
            }
        ]

    monkeypatch.setattr(builder, "request_romanization_corrections", fake_repair)
    repaired = builder.repair_invalid_romanization_rows(
        tasks, [valid_row, invalid_row], "gpt-5.6-luna"
    )

    assert calls == [[2]]
    assert repaired[0] is valid_row
    assert repaired[1]["word"] == "sù-nák"
    builder.validate_language(repaired, tasks, "Thai (Paiboon romanization)")


def test_romanization_partition_rejects_non_latin_letters_and_changed_sense():
    tasks = [
        {"id": 1, "word": "แมว", "sentence": "แมวนอน", "sense": "cat"},
        {"id": 2, "word": "สุนัข", "sentence": "สุนัขนอน", "sense": "dog"},
    ]
    rows = [
        {"id": 1, "word": "мɛɛo", "sentence": "мɛɛo nɔɔn.", "sense": "cat"},
        {"id": 2, "word": "sù-nák", "sentence": "Sù-nák nɔɔn.", "sense": "hound"},
    ]

    valid, invalid = builder.partition_romanization_rows(rows, tasks)

    assert valid == {}
    assert [task["id"] for task in invalid] == [1, 2]
