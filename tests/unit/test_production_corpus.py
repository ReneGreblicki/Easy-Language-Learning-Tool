from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyRepository


def test_packaged_corpus_integrity_and_mobile_parity() -> None:
    root = Path(__file__).parents[2]
    data_root = root / "resources" / "frequency_data"
    manifest = json.loads((data_root / "MULTISOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    desktop = (data_root / "production" / "words.jsonl.gz").read_bytes()
    mobile = (root / "android_app" / "assets" / "frequency" / "words.jsonl.gz").read_bytes()
    assert hashlib.sha256(desktop).hexdigest() == manifest["generated_corpus_sha256"]
    assert mobile == desktop
    # Read to EOF to validate gzip's CRC and length, then validate every JSON row.
    rows = [json.loads(line) for line in gzip.decompress(desktop).decode("utf-8").splitlines()]
    assert len(rows) == manifest["output_records"]


def test_production_corpus_has_5000_ranked_words_per_language() -> None:
    source = (
        Path(__file__).parents[2] / "resources" / "frequency_data" / "production" / "words.jsonl.gz"
    )
    repository = FrequencyRepository.from_jsonl(source)
    assert repository.validate_release_readiness(5_000) == []
    for learning in Language:
        translation = next(language for language in Language if language is not learning)
        assert repository.available_count(learning, translation) == 5_000


def test_thai_corpora_have_distinct_scripts_and_attribution() -> None:
    source = (
        Path(__file__).parents[2] / "resources" / "frequency_data" / "production" / "words.jsonl.gz"
    )
    repository = FrequencyRepository.from_jsonl(source)
    script = [record for record in repository.records if record.language is Language.THAI_SCRIPT]
    paiboon = [record for record in repository.records if record.language is Language.THAI_PAIBOON]
    assert len(script) == len(paiboon) == 5_000
    assert all(
        any("\u0e00" <= character <= "\u0e7f" for character in record.lemma) for record in script
    )
    assert all(
        not any("\u0e00" <= character <= "\u0e7f" for character in record.lemma)
        for record in paiboon
    )
    assert all("Phupha" in record.source and "Kaikki" in record.source for record in script)
    assert all("CC0" in record.licence and "CC BY-SA" in record.licence for record in paiboon)


def test_multisource_expansion_has_native_scripts_and_additive_provenance() -> None:
    source = (
        Path(__file__).parents[2] / "resources" / "frequency_data" / "production" / "words.jsonl.gz"
    )
    repository = FrequencyRepository.from_jsonl(source)
    script_ranges = {
        Language.SIMPLIFIED_CHINESE: ((0x3400, 0x9FFF), (0xF900, 0xFAFF)),
        Language.JAPANESE: ((0x3040, 0x30FF), (0x3400, 0x9FFF)),
        Language.KOREAN: ((0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF)),
        Language.MALAYALAM: ((0x0D00, 0x0D7F),),
        Language.RUSSIAN: ((0x0400, 0x052F),),
    }
    for language, ranges in script_ranges.items():
        records = [record for record in repository.records if record.language is language]
        assert len(records) == 5_000
        assert all(
            any(
                start <= ord(character) <= end
                for character in record.lemma
                for start, end in ranges
            )
            for record in records
        )

    expanded = [record for record in repository.records if record.language is Language.POLISH]
    assert all("wordfreq" in record.source for record in expanded)
    assert all("OpenSubtitles" in record.source for record in expanded)
    assert all("frekwencja" in record.source for record in expanded)
    assert all("Wiktionary" in record.licence for record in expanded)
