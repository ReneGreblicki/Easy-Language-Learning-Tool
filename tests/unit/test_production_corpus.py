from __future__ import annotations

from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyRepository


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
