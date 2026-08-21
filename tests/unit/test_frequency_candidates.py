from __future__ import annotations

import csv
import json
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from tools.audit_frequency_review import audit
from tools.build_frequency_candidates import extract_candidates, write_review_tsv


def test_candidate_extraction_filters_forms_and_ranks_unique_lemmas(tmp_path: Path) -> None:
    entries = [
        {
            "word": "go",
            "pos": "verb",
            "translations": [
                {"code": "es", "word": "ir"},
                {"code": "de", "word": "gehen"},
                {"code": "pt", "word": "ir"},
                {"code": "fr", "word": "aller"},
            ],
            "forms": [{"form": "went", "tags": ["past"]}],
        },
        {
            "word": "walked",
            "pos": "verb",
            "senses": [{"form_of": [{"word": "walk"}], "tags": ["form-of"]}],
        },
        {"word": "house", "pos": "noun"},
        {"word": "andare", "pos": "verb", "lang_code": "it"},
        {
            "word": "be",
            "pos": "verb",
            "tags": ["irregular"],
            "translations": [{"code": "de", "word": "sein"}],
        },
    ]
    source = tmp_path / "english.jsonl"
    source.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

    rows = extract_candidates(
        source,
        Language.US_ENGLISH,
        "enwiktionary-2026-08-05",
        frequency=lambda word, _language: {"be": 7.0, "go": 6.0}[word],
    )

    assert [row["lemma"] for row in rows] == ["be", "go"]
    assert [row["candidate_rank"] for row in rows] == ["1", "2"]
    assert rows[0]["irregularity"] == "irregular"
    assert rows[1]["es-ES"] == "ir"
    assert rows[1]["supported_constructions"] == "past"
    assert rows[1]["review_status"] == "candidate"

    output = tmp_path / "review.tsv"
    write_review_tsv(output, rows)
    with output.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle, delimiter="\t"))
    assert len(written) == 2
    assert written[0]["source_revision"] == "enwiktionary-2026-08-05"
    errors, summaries = audit(output)
    assert errors == []
    assert len(summaries) == 5
