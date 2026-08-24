from __future__ import annotations

import argparse
import csv
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyWord, write_frequency_jsonl


def build(source: Path, destination: Path) -> None:
    """Compile an automatically enriched and validated TSV into the app's JSONL corpus."""
    records: list[FrequencyWord] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            language = Language(raw["language"])
            lemma = raw["lemma"].strip()
            if raw.get("validation_status", "").strip() != "automated":
                raise ValueError(f"{language.label} '{lemma}' has not passed automated validation.")
            translations = {
                target: raw.get(target.value, "").strip()
                for target in Language
                if target is not language
            }
            translations = {target: value for target, value in translations.items() if value}
            records.append(
                FrequencyWord(
                    language=language,
                    rank=int(raw["rank"]),
                    lemma=lemma,
                    part_of_speech=raw["part_of_speech"].strip(),
                    forms=tuple(
                        item.strip() for item in raw.get("forms", "").split("|") if item.strip()
                    ),
                    translations=translations,
                    confidence=raw.get("confidence", "automated").strip(),
                    source=raw["source"].strip(),
                    licence=raw["licence"].strip(),
                    source_url=raw["source_url"].strip(),
                    source_revision=raw["source_revision"].strip(),
                    validation_status="automated",
                )
            )
    write_frequency_jsonl(destination, records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile the automated word-frequency TSV.")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    build(arguments.source, arguments.destination)


if __name__ == "__main__":
    main()
