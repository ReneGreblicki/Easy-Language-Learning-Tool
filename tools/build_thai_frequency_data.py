from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import (
    FrequencyRepository,
    FrequencyWord,
    write_frequency_jsonl,
)

THAI_WORD = re.compile(r"[\u0E00-\u0E7F]{2,}")
EXCLUDED_PARTS_OF_SPEECH = {"character", "infix", "name", "prefix", "punct", "suffix", "symbol"}
EXCLUDED_TAGS = {
    "archaic",
    "dated",
    "historical",
    "nonstandard",
    "obsolete",
    "rare",
    "slang",
    "vulgar",
}
SOURCE = "OpenSubtitles 2018 + Phupha 2026 ranking; Kaikki/Wiktionary lexical data"
LICENCE = (
    "CC BY-SA 4.0 (OpenSubtitles frequency data); CC0 1.0 (Phupha data); "
    "CC BY-SA 3.0 and GFDL (Wiktionary)"
)
SOURCE_URL = (
    "https://github.com/hermitdave/FrequencyWords | "
    "https://github.com/PyThaiNLP/Phupha-Word-freq | "
    "https://kaikki.org/dictionary/Thai/"
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _is_usable(entry: dict[str, Any]) -> bool:
    word = _clean(entry.get("word"))
    if THAI_WORD.fullmatch(word) is None or _clean(entry.get("pos")) in EXCLUDED_PARTS_OF_SPEECH:
        return False
    senses = [sense for sense in entry.get("senses") or [] if isinstance(sense, dict)]
    if not senses:
        return False
    return any(not (set(sense.get("tags") or []) & EXCLUDED_TAGS) for sense in senses)


def _paiboon(entry: dict[str, Any]) -> str:
    for sound in entry.get("sounds") or []:
        if isinstance(sound, dict) and "Paiboon" in set(sound.get("raw_tags") or []):
            value = _clean(sound.get("roman"))
            if value:
                return value
    return ""


def load_lexicon(path: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid Kaikki JSON on line {line_number}.") from error
            if not _is_usable(entry):
                continue
            word = _clean(entry.get("word"))
            previous = entries.get(word)
            if previous is None or (_paiboon(entry) and not _paiboon(previous)):
                entries[word] = entry
    return entries


def opensubtitles_order(path: Path, lexicon: dict[str, dict[str, Any]]) -> list[str]:
    ranked: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                word, _count = line.rstrip().rsplit(" ", 1)
            except ValueError:
                continue
            if word in lexicon and word not in ranked:
                ranked.append(word)
    return ranked


def phupha_order(path: Path, lexicon: dict[str, dict[str, Any]]) -> list[str]:
    counts: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            word = _clean(row.get("word"))
            if word in lexicon:
                counts.append((int(row["count"]), word))
    counts.sort(key=lambda item: (-item[0], item[1]))
    return [word for _count, word in counts]


def merge_rankings(*rankings: Iterable[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for ranking in rankings:
        for word in ranking:
            normalized = word.casefold()
            if normalized not in seen:
                selected.append(word)
                seen.add(normalized)
    return selected


def _forms(entry: dict[str, Any], word: str) -> tuple[str, ...]:
    forms = {word}
    for raw in entry.get("forms") or []:
        if not isinstance(raw, dict) or set(raw.get("tags") or []) & EXCLUDED_TAGS:
            continue
        form = _clean(raw.get("form"))
        if THAI_WORD.fullmatch(form):
            forms.add(form)
    return tuple(sorted(forms, key=str.casefold))


def _record(
    language: Language,
    rank: int,
    lemma: str,
    part_of_speech: str,
    forms: tuple[str, ...],
    source_revision: str,
) -> FrequencyWord:
    return FrequencyWord(
        language=language,
        rank=rank,
        lemma=lemma,
        part_of_speech=part_of_speech or "unknown",
        forms=forms or (lemma,),
        translations={},
        confidence="automated-cross-source",
        source=SOURCE,
        licence=LICENCE,
        source_url=SOURCE_URL,
        source_revision=source_revision,
        validation_status="automated",
    )


def build(
    corpus: Path,
    phupha: Path,
    opensubtitles: Path,
    kaikki: Path,
    destination: Path,
    source_revision: str,
    limit: int = 5_000,
) -> None:
    existing = [
        record
        for record in FrequencyRepository.from_jsonl(corpus).records
        if record.language not in {Language.THAI_SCRIPT, Language.THAI_PAIBOON}
    ]
    lexicon = load_lexicon(kaikki)
    ranking = merge_rankings(
        opensubtitles_order(opensubtitles, lexicon),
        phupha_order(phupha, lexicon),
    )
    if len(ranking) < limit:
        raise ValueError(f"Only {len(ranking):,} validated Thai candidates; {limit:,} required.")

    script_records: list[FrequencyWord] = []
    romanized_records: list[FrequencyWord] = []
    seen_romanized: set[str] = set()
    for word in ranking:
        entry = lexicon[word]
        part_of_speech = _clean(entry.get("pos")) or "unknown"
        if len(script_records) < limit:
            script_records.append(
                _record(
                    Language.THAI_SCRIPT,
                    len(script_records) + 1,
                    word,
                    part_of_speech,
                    _forms(entry, word),
                    source_revision,
                )
            )

        paiboon = _paiboon(entry)
        normalized = paiboon.casefold().strip()
        if normalized and normalized not in seen_romanized and len(romanized_records) < limit:
            romanized_records.append(
                _record(
                    Language.THAI_PAIBOON,
                    len(romanized_records) + 1,
                    paiboon,
                    part_of_speech,
                    (paiboon,),
                    source_revision,
                )
            )
            seen_romanized.add(normalized)
        if len(script_records) == limit and len(romanized_records) == limit:
            break

    if len(romanized_records) != limit:
        raise ValueError(
            f"Only {len(romanized_records):,} unique romanizations; {limit:,} required."
        )
    write_frequency_jsonl(destination, existing + script_records + romanized_records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add validated Thai script and romanized data.")
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--phupha", required=True, type=Path)
    parser.add_argument("--opensubtitles", required=True, type=Path)
    parser.add_argument("--kaikki", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--limit", type=int, default=5_000)
    arguments = parser.parse_args()
    build(
        arguments.corpus,
        arguments.phupha,
        arguments.opensubtitles,
        arguments.kaikki,
        arguments.destination,
        arguments.source_revision,
        arguments.limit,
    )


if __name__ == "__main__":
    main()
