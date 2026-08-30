from __future__ import annotations

import argparse
import re
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyWord, write_frequency_jsonl

VALID_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
WORDFREQ_LANGUAGES = tuple(
    language
    for language in Language
    if language not in {Language.THAI_SCRIPT, Language.THAI_PAIBOON}
)


def build(destination: Path, limit: int = 5_000) -> None:
    """Build the reproducible runtime ranking; Kaikki enrichment can replace records later."""
    try:
        from wordfreq import top_n_list
    except ImportError as error:
        raise SystemExit("Install the data-build extra before running this tool.") from error

    records: list[FrequencyWord] = []
    for language in WORDFREQ_LANGUAGES:
        code = language.value.split("-")[0]
        seen: set[str] = set()
        selected: list[str] = []
        candidate_limit = max(limit * 3, 20_000)
        for raw in top_n_list(code, candidate_limit):
            word = " ".join(raw.split()).strip()
            normalized = word.casefold()
            if (
                not word
                or normalized in seen
                or len(word) > 80
                or VALID_WORD.fullmatch(word) is None
            ):
                continue
            seen.add(normalized)
            selected.append(word)
            if len(selected) == limit:
                break
        if len(selected) != limit:
            raise ValueError(f"{language.label}: found {len(selected):,}; {limit:,} required.")
        for rank, word in enumerate(selected, 1):
            records.append(
                FrequencyWord(
                    language=language,
                    rank=rank,
                    lemma=word,
                    part_of_speech="unknown",
                    forms=(word,),
                    translations={},
                    confidence="wordfreq-baseline",
                    source="wordfreq 3.x multilingual frequency data",
                    licence="CC BY-SA 4.0 (data); Apache-2.0 (code)",
                    source_url="https://github.com/rspeer/wordfreq",
                    source_revision="wordfreq-3.1.1",
                    validation_status="automated",
                )
            )
    write_frequency_jsonl(destination, records)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build six wordfreq baselines; Thai is built with the Thai pipeline."
    )
    parser.add_argument(
        "destination",
        type=Path,
        nargs="?",
        default=Path("resources/frequency_data/production/words.jsonl.gz"),
    )
    parser.add_argument("--limit", type=int, default=5_000)
    arguments = parser.parse_args()
    build(arguments.destination, arguments.limit)


if __name__ == "__main__":
    main()
