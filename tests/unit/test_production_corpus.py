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
