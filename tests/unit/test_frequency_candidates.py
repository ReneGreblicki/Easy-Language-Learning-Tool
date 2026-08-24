from __future__ import annotations

import csv
import json
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from tools.build_frequency_candidates import extract_candidates, write_tsv


def test_candidate_extraction_supports_all_parts_of_speech_and_filters_form_entries(
    tmp_path: Path,
) -> None:
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
        top_words=["be", "go", "house", "walked"],
    )

    assert [row["lemma"] for row in rows] == ["be", "go", "house", "walked"]
    assert [row["rank"] for row in rows] == ["1", "2", "3", "4"]
    assert rows[1]["es-ES"] == "ir"
    assert rows[1]["forms"] == "go|went"
    assert rows[2]["part_of_speech"] == "noun"
    assert rows[0]["validation_status"] == "automated"
    assert rows[3]["part_of_speech"] == "unknown"

    output = tmp_path / "candidates.tsv"
    write_tsv(output, rows)
    with output.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle, delimiter="\t"))
    assert len(written) == 4
    assert written[0]["source_revision"] == "enwiktionary-2026-08-05"
