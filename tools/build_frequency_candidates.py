from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections.abc import Callable, Iterable, Iterator
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
}
LANGUAGE_CODES: dict[Language, str] = {
    language: language.value.split("-")[0] for language in Language
}
TARGET_BY_CODE = {code: language for language, code in LANGUAGE_CODES.items()}
FIELDS = (
    "language",
    "candidate_rank",
    "zipf_frequency",
    "lemma",
    "en-US",
    "es-ES",
    "de-DE",
    "pt-PT",
    "fr-FR",
    "irregularity",
    "supported_constructions",
    "confidence",
    "source",
    "licence",
    "source_url",
    "source_revision",
    "review_status",
    "reviewer",
    "reviewed_at",
    "usage_flags",
    "locale_flags",
    "review_notes",
)
INVALID_LEMMA = re.compile(r"[\d\n\r\t]")
USAGE_MARKERS = {
    "archaic",
    "dated",
    "historical",
    "nonstandard",
    "obsolete",
    "rare",
    "slang",
    "vulgar",
}
LOCALE_MARKERS = {
    "Australia",
    "Austria",
    "Belgium",
    "Brazil",
    "Canada",
    "France",
    "Germany",
    "Latin-America",
    "Mexico",
    "New-Zealand",
    "Portugal",
    "Spain",
    "Switzerland",
    "UK",
    "US",
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


def _is_form_entry(entry: dict[str, Any]) -> bool:
    senses = [sense for sense in entry.get("senses") or [] if isinstance(sense, dict)]
    return bool(senses) and all(
        sense.get("form_of") or "form-of" in set(sense.get("tags") or []) for sense in senses
    )


def _first_gloss(entry: dict[str, Any]) -> str:
    for sense in entry.get("senses") or []:
        if not isinstance(sense, dict) or sense.get("form_of"):
            continue
        for gloss in sense.get("glosses") or []:
            cleaned = _clean(gloss)
            if cleaned:
                return cleaned
    return ""


def _translations(entry: dict[str, Any], source_language: Language) -> dict[Language, str]:
    translations: dict[Language, str] = {source_language: _clean(entry.get("word"))}
    for raw in entry.get("translations") or []:
        if not isinstance(raw, dict):
            continue
        target = TARGET_BY_CODE.get(_clean(raw.get("code") or raw.get("lang_code")))
        word = _clean(raw.get("word"))
        if target is not None and target not in translations and word:
            translations[target] = word
    if source_language is not Language.US_ENGLISH and Language.US_ENGLISH not in translations:
        gloss = _first_gloss(entry)
        if gloss:
            translations[Language.US_ENGLISH] = gloss
    return translations


def _constructions(entry: dict[str, Any]) -> str:
    supported: set[str] = set()
    vocabulary = {
        "present",
        "past",
        "preterite",
        "participle",
        "imperative",
        "subjunctive",
        "conditional",
        "infinitive",
    }
    for form in entry.get("forms") or []:
        if not isinstance(form, dict):
            continue
        supported.update(tag for tag in form.get("tags") or [] if tag in vocabulary)
    return "|".join(sorted(supported))


def _entry_tags(entry: dict[str, Any]) -> set[str]:
    tags = set(entry.get("tags") or [])
    for sense in entry.get("senses") or []:
        if isinstance(sense, dict):
            tags.update(sense.get("tags") or [])
    return tags


def extract_candidates(
    source: Path,
    language: Language,
    source_revision: str,
    frequency: Callable[[str, str], float] | None = None,
) -> list[dict[str, str]]:
    if frequency is None:
        try:
            from wordfreq import zipf_frequency
        except ImportError as error:
            raise SystemExit(
                "Install the data-build extra containing wordfreq before running this tool."
            ) from error
        frequency = zipf_frequency

    candidates: dict[str, dict[str, str]] = {}
    with _open_text(source) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on {source}:{line_number}.") from error
            entry_language = _clean(entry.get("lang_code"))
            if entry_language and entry_language != LANGUAGE_CODES[language]:
                continue
            if entry.get("pos") != "verb" or _is_form_entry(entry):
                continue
            lemma = _clean(entry.get("word"))
            normalized = lemma.casefold()
            if not lemma or len(lemma) > 80 or INVALID_LEMMA.search(lemma):
                continue
            translations = _translations(entry, language)
            tags = _entry_tags(entry)
            row = {
                "language": language.value,
                "candidate_rank": "0",
                "zipf_frequency": f"{frequency(lemma, LANGUAGE_CODES[language]):.4f}",
                "lemma": lemma,
                **{target.value: translations.get(target, "") for target in Language},
                "irregularity": "irregular" if "irregular" in tags else "unknown",
                "supported_constructions": _constructions(entry),
                "confidence": "dictionary-candidate",
                "source": f"Kaikki/Wiktionary {LANGUAGE_NAMES[language]} dictionary",
                "licence": "CC BY-SA 3.0 and GFDL",
                "source_url": f"https://kaikki.org/dictionary/{LANGUAGE_NAMES[language]}/index.html",
                "source_revision": source_revision,
                "review_status": "candidate",
                "reviewer": "",
                "reviewed_at": "",
                "usage_flags": "|".join(sorted(tags & USAGE_MARKERS)),
                "locale_flags": "|".join(sorted(tags & LOCALE_MARKERS)),
                "review_notes": "",
            }
            existing = candidates.get(normalized)
            if existing is None or sum(bool(row[target.value]) for target in Language) > sum(
                bool(existing[target.value]) for target in Language
            ):
                candidates[normalized] = row
    ranked = sorted(
        candidates.values(),
        key=lambda row: (-float(row["zipf_frequency"]), row["lemma"].casefold()),
    )
    for rank, row in enumerate(ranked, 1):
        row["candidate_rank"] = str(rank)
    return ranked


def write_review_tsv(path: Path, rows: Iterable[dict[str, str]]) -> None:
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
            "Use LANGUAGE=PATH, for example de-DE=german.jsonl"
        ) from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a frequency-ranked human-review TSV from Kaikki/Wiktionary JSONL data."
    )
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        type=_parse_input,
        metavar="LANGUAGE=PATH",
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    rows: list[dict[str, str]] = []
    for language, source in arguments.input:
        rows.extend(extract_candidates(source, language, arguments.source_revision))
    write_review_tsv(arguments.output, rows)


if __name__ == "__main__":
    main()
