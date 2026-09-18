from __future__ import annotations

import argparse
import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import (
    FrequencyRepository,
    FrequencyWord,
    write_frequency_jsonl,
)

FREQUENCYWORDS_REVISION = "525f9b560de45753a5ea01069454e72e9aa541c6"
FREKWENCJA_REVISION = "04f5cdd221c832c08ac3309654c340044b833468"
SOURCE = (
    "wordfreq 3.1.1 ranking + Wiktionary-listed OpenSubtitles 2018 ranking + "
    "frekwencja/wordfrequency.info agreement"
)
LICENCE = (
    "CC BY-SA 4.0 (wordfreq/OpenSubtitles data); wordfrequency.info free sample and "
    "upstream source terms (frekwencja agreement signal); CC BY-SA 3.0 and GFDL "
    "(optional Kaikki/Wiktionary enrichment)"
)
SOURCE_URL = (
    "https://github.com/rspeer/wordfreq | "
    "https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists | "
    "https://github.com/hermitdave/FrequencyWords | "
    "https://github.com/frekwencja/most-common-words-multilingual | "
    "https://wordfrequency.info/samples.asp | "
    "https://kaikki.org/dictionary/rawdata.html"
)


@dataclass(frozen=True)
class SourceConfig:
    wordfreq: str | None
    frequencywords: str
    frekwencja: str


SOURCE_CONFIGS: dict[Language, SourceConfig] = {
    Language.POLISH: SourceConfig("pl", "pl", "pl"),
    Language.DUTCH: SourceConfig("nl", "nl", "nl"),
    Language.DANISH: SourceConfig("da", "da", "da"),
    Language.CROATIAN: SourceConfig("sh", "hr", "hr"),
    Language.VIETNAMESE: SourceConfig("vi", "vi", "vi"),
    Language.SIMPLIFIED_CHINESE: SourceConfig("zh", "zh_cn", "zh-CN"),
    Language.MALAYALAM: SourceConfig(None, "ml", "ml"),
    Language.SLOVAK: SourceConfig("sk", "sk", "sk"),
    Language.RUSSIAN: SourceConfig("ru", "ru", "ru"),
    Language.NORWEGIAN: SourceConfig("nb", "no", "no"),
    Language.KOREAN: SourceConfig("ko", "ko", "ko"),
    Language.HUNGARIAN: SourceConfig("hu", "hu", "hu"),
    Language.SWEDISH: SourceConfig("sv", "sv", "sv"),
    Language.INDONESIAN: SourceConfig("id", "id", "id"),
    Language.JAPANESE: SourceConfig("ja", "ja", "ja"),
    Language.TURKISH: SourceConfig("tr", "tr", "tr"),
}

SCRIPT_RANGES: dict[Language, tuple[tuple[int, int], ...]] = {
    Language.SIMPLIFIED_CHINESE: ((0x3400, 0x9FFF), (0xF900, 0xFAFF)),
    Language.JAPANESE: (
        (0x3040, 0x30FF),
        (0x3400, 0x9FFF),
        (0xF900, 0xFAFF),
    ),
    Language.KOREAN: ((0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF)),
    Language.MALAYALAM: ((0x0D00, 0x0D7F),),
    Language.RUSSIAN: ((0x0400, 0x052F),),
}


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _has_script(value: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= ord(character) <= end for character in value for start, end in ranges)


def valid_term(language: Language, raw: str) -> bool:
    term = unicodedata.normalize("NFKC", raw).strip()
    if not term or len(term) > 80 or any(character.isspace() for character in term):
        return False
    if any(
        character.isdigit() or unicodedata.category(character).startswith("C") for character in term
    ):
        return False
    allowed_punctuation = {"'", "’", "-"}
    if any(
        unicodedata.category(character).startswith(("P", "S"))
        and character not in allowed_punctuation
        for character in term
    ):
        return False
    ranges = SCRIPT_RANGES.get(language)
    if ranges is not None and not _has_script(term, ranges):
        return False
    return any(character.isalpha() for character in term)


def _deduplicate(values: list[str], language: Language, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = unicodedata.normalize("NFKC", value).strip()
        key = _normalized(term)
        if key in seen or not valid_term(language, term):
            continue
        seen.add(key)
        result.append(term)
        if len(result) == limit:
            break
    return result


def read_frequencywords(root: Path, config: SourceConfig, language: Language) -> list[str]:
    directory = root / "content" / "2018" / config.frequencywords
    preferred = directory / f"{config.frequencywords}_50k.txt"
    source = preferred if preferred.exists() else directory / f"{config.frequencywords}_full.txt"
    if not source.exists():
        raise FileNotFoundError(f"Missing OpenSubtitles ranking: {source}")
    values: list[str] = []
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            value, separator, count = line.rstrip().rpartition(" ")
            if separator and count.isdigit():
                values.append(value)
    return _deduplicate(values, language, 60_000)


def read_frekwencja(root: Path, config: SourceConfig, language: Language) -> list[str]:
    source = root / "data" / "wordfrequency.info" / f"{config.frekwencja}.txt"
    if not source.exists():
        raise FileNotFoundError(f"Missing frekwencja ranking: {source}")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    return _deduplicate([row[0] for row in rows[1:] if row], language, 5_050)


def read_wordfreq(config: SourceConfig, language: Language) -> list[str]:
    if config.wordfreq is None:
        return []
    try:
        from wordfreq import top_n_list
    except ImportError as error:
        raise SystemExit("Install the data-build extra before running this tool.") from error
    return _deduplicate(top_n_list(config.wordfreq, 60_000), language, 60_000)


def merge_rankings(
    language: Language,
    wordfreq: list[str],
    opensubtitles: list[str],
    frekwencja: list[str],
    *,
    limit: int = 5_000,
) -> list[str]:
    """Return a native-corpus-gated weighted consensus ranking.

    The supplied frekwencja data is a translation of an English ranking. It has
    substantial influence when it agrees with native corpora, but it can never
    introduce a term that appears only in the translated list.
    """
    if wordfreq:
        sources = ((wordfreq, 0.45), (opensubtitles, 0.35), (frekwencja, 0.20))
        native = wordfreq + opensubtitles
    else:
        sources = ((opensubtitles, 0.65), (frekwencja, 0.35))
        native = opensubtitles

    display: dict[str, str] = {}
    for value in native:
        display.setdefault(_normalized(value), value)
    ranks = [
        {_normalized(value): rank for rank, value in enumerate(values, 1)}
        for values, _weight in sources
    ]
    scored: list[tuple[float, int, str, str]] = []
    for key, value in display.items():
        score = 0.0
        agreements = 0
        for (values, weight), source_ranks in zip(sources, ranks, strict=True):
            source_rank = source_ranks.get(key)
            if source_rank is None:
                score += weight * 1.25
            else:
                score += weight * (source_rank / max(len(values), 1))
                agreements += 1
        scored.append((score, -agreements, key, value))
    scored.sort()
    result = [value for _score, _agreements, _key, value in scored[:limit]]
    if len(result) != limit:
        raise ValueError(f"{language.label}: found {len(result):,}; {limit:,} required.")
    return result


def build(
    destination: Path,
    frequencywords_root: Path,
    frekwencja_root: Path,
    *,
    base: Path | None = None,
    limit: int = 5_000,
) -> None:
    replaced = set(SOURCE_CONFIGS)
    records = (
        [
            record
            for record in FrequencyRepository.from_jsonl(base).records
            if record.language not in replaced
        ]
        if base is not None
        else []
    )
    for language, config in SOURCE_CONFIGS.items():
        wordfreq = read_wordfreq(config, language)
        opensubtitles = read_frequencywords(frequencywords_root, config, language)
        translated = read_frekwencja(frekwencja_root, config, language)
        ranking = merge_rankings(language, wordfreq, opensubtitles, translated, limit=limit)
        revision = (
            f"wordfreq-3.1.1; FrequencyWords-{FREQUENCYWORDS_REVISION[:12]}; "
            f"frekwencja-{FREKWENCJA_REVISION[:12]}"
        )
        records.extend(
            FrequencyWord(
                language=language,
                rank=rank,
                lemma=word,
                part_of_speech="unknown",
                forms=(word,),
                translations={},
                confidence="automated-three-source-consensus"
                if wordfreq
                else "automated-two-source-consensus",
                source=SOURCE,
                licence=LICENCE,
                source_url=SOURCE_URL,
                source_revision=revision,
                validation_status="automated",
            )
            for rank, word in enumerate(ranking, 1)
        )
    records.sort(key=lambda record: (list(Language).index(record.language), record.rank))
    write_frequency_jsonl(destination, list(records))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build additive weighted multilingual rankings.")
    parser.add_argument("--frequencywords-root", required=True, type=Path)
    parser.add_argument("--frekwencja-root", required=True, type=Path)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--limit", type=int, default=5_000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("resources/frequency_data/production/words.jsonl.gz"),
    )
    arguments = parser.parse_args()
    build(
        arguments.output,
        arguments.frequencywords_root,
        arguments.frekwencja_root,
        base=arguments.base,
        limit=arguments.limit,
    )


if __name__ == "__main__":
    main()
