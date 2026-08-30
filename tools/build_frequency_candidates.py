from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

from easy_language_learning_tool.domain.enums import Language

LANGUAGE_NAMES: dict[Language, str] = {
    Language.US_ENGLISH: "English",
    Language.EUROPEAN_SPANISH: "Spanish",
    Language.GERMAN: "German",
    Language.EUROPEAN_PORTUGUESE: "Portuguese",
    Language.FRENCH: "French",
    Language.ITALIAN: "Italian",
    Language.THAI_SCRIPT: "Thai",
    Language.THAI_PAIBOON: "Thai",
}
LANGUAGE_CODES = {language: language.value.split("-")[0] for language in Language}
TARGET_BY_CODE = {
    "en": Language.US_ENGLISH,
    "es": Language.EUROPEAN_SPANISH,
    "de": Language.GERMAN,
    "pt": Language.EUROPEAN_PORTUGUESE,
    "fr": Language.FRENCH,
    "it": Language.ITALIAN,
    "th": Language.THAI_SCRIPT,
}
FIELDS = (
    "language",
    "rank",
    "lemma",
    "part_of_speech",
    "forms",
    "en-US",
    "es-ES",
    "de-DE",
    "pt-PT",
    "fr-FR",
    "it-IT",
    "th-Thai-TH",
    "th-Latn-TH",
    "confidence",
    "source",
    "licence",
    "source_url",
    "source_revision",
    "validation_status",
    "validation_notes",
)
INVALID_WORD = re.compile(r"[\d\n\r\t]")
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


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


@contextmanager
def _open_text(source: Path) -> Iterator[TextIO]:
    if source.suffix.casefold() == ".gz":
        with gzip.open(source, mode="rt", encoding="utf-8") as handle:
            yield handle
    else:
        with source.open(mode="r", encoding="utf-8") as handle:
            yield handle


def _entry_tags(entry: dict[str, Any]) -> set[str]:
    tags = set(entry.get("tags") or [])
    for sense in entry.get("senses") or []:
        if isinstance(sense, dict):
            tags.update(sense.get("tags") or [])
    return tags


def _is_form_entry(entry: dict[str, Any]) -> bool:
    senses = [sense for sense in entry.get("senses") or [] if isinstance(sense, dict)]
    return bool(senses) and all(
        sense.get("form_of") or "form-of" in set(sense.get("tags") or []) for sense in senses
    )


def _forms(entry: dict[str, Any], lemma: str) -> str:
    values = {lemma}
    for raw in entry.get("forms") or []:
        if isinstance(raw, dict):
            form = _clean(raw.get("form"))
            if form and len(form) <= 80 and not INVALID_WORD.search(form):
                values.add(form)
    return "|".join(sorted(values, key=str.casefold))


def _translations(entry: dict[str, Any]) -> dict[Language, str]:
    result: dict[Language, str] = {}
    for raw in entry.get("translations") or []:
        if not isinstance(raw, dict):
            continue
        target = TARGET_BY_CODE.get(_clean(raw.get("code") or raw.get("lang_code")))
        word = _clean(raw.get("word"))
        if target is not None and target not in result and word:
            result[target] = word
    return result


def extract_candidates(
    source: Path,
    language: Language,
    source_revision: str,
    *,
    limit: int = 5_000,
    top_words: list[str] | None = None,
) -> list[dict[str, str]]:
    """Join wordfreq's deterministic ranking to Kaikki POS, forms, and translations."""
    if top_words is None:
        try:
            from wordfreq import top_n_list
        except ImportError as error:
            raise SystemExit("Install the data-build extra before running this tool.") from error
        top_words = top_n_list(LANGUAGE_CODES[language], max(limit * 3, 10_000))

    wanted = {word.casefold() for word in top_words}
    entries: dict[str, dict[str, Any]] = {}
    with _open_text(source) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on {source}:{line_number}.") from error
            if _clean(entry.get("lang_code")) not in {"", LANGUAGE_CODES[language]}:
                continue
            lemma = _clean(entry.get("word"))
            key, pos = lemma.casefold(), _clean(entry.get("pos"))
            if (
                key not in wanted
                or not lemma
                or not pos
                or len(lemma) > 80
                or INVALID_WORD.search(lemma)
                or _is_form_entry(entry)
                or _entry_tags(entry) & EXCLUDED_TAGS
            ):
                continue
            previous = entries.get(key)
            if previous is None or len(entry.get("forms") or []) > len(previous.get("forms") or []):
                entries[key] = entry

    rows: list[dict[str, str]] = []
    for word in top_words[:limit]:
        entry = entries.get(word.casefold())
        lemma = _clean(entry.get("word")) if entry is not None else word
        translations = _translations(entry) if entry is not None else {}
        rows.append(
            {
                "language": language.value,
                "rank": str(len(rows) + 1),
                "lemma": lemma,
                "part_of_speech": _clean(entry.get("pos")) if entry is not None else "unknown",
                "forms": _forms(entry, lemma) if entry is not None else lemma,
                **{target.value: translations.get(target, "") for target in Language},
                "confidence": "wordfreq-kaikki",
                "source": "wordfreq 3.x ranking + Kaikki/Wiktionary lexical data",
                "licence": "CC BY-SA 4.0 (wordfreq data); CC BY-SA 3.0 and GFDL (Wiktionary)",
                "source_url": "https://github.com/rspeer/wordfreq | https://kaikki.org/dictionary/rawdata.html",
                "source_revision": source_revision,
                "validation_status": "automated",
                "validation_notes": "Translation generated and validated with each example"
                if any(
                    target is not language and not translations.get(target) for target in Language
                )
                else "Dictionary translations present",
            }
        )
    return rows


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_input(value: str) -> tuple[Language, Path]:
    try:
        language_value, path = value.split("=", 1)
        return Language(language_value), Path(path)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Use LANGUAGE=PATH, for example it-IT=italian.jsonl"
        ) from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build ranked all-word candidates from wordfreq and Kaikki."
    )
    parser.add_argument("--input", action="append", required=True, type=_parse_input)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--limit", type=int, default=5_000)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    rows: list[dict[str, str]] = []
    for language, source in arguments.input:
        rows.extend(
            extract_candidates(source, language, arguments.source_revision, limit=arguments.limit)
        )
    write_tsv(arguments.output, rows)


if __name__ == "__main__":
    main()
