from __future__ import annotations

import argparse
import csv
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyVerb, write_frequency_jsonl


def build(source: Path, destination: Path) -> None:
    """Rank a reviewed verb lexicon with wordfreq while preserving licence metadata."""
    try:
        from wordfreq import zipf_frequency
    except ImportError as error:
        raise SystemExit(
            "Install the data build extra containing wordfreq before running this tool."
        ) from error

    rows: list[tuple[float, FrequencyVerb]] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            language = Language(raw["language"])
            lemma = raw["lemma"].strip()
            language_code = language.value.split("-")[0]
            translations = {
                Language(key): value
                for key, value in (
                    ("en-US", raw.get("en-US", "")),
                    ("es-ES", raw.get("es-ES", "")),
                    ("de-DE", raw.get("de-DE", "")),
                    ("pt-PT", raw.get("pt-PT", "")),
                    ("fr-FR", raw.get("fr-FR", "")),
                )
                if value and key != language.value
            }
            rows.append(
                (
                    zipf_frequency(lemma, language_code),
                    FrequencyVerb(
                        language=language,
                        rank=1,
                        lemma=lemma,
                        translations=translations,
                        irregularity=raw.get("irregularity", "unknown"),
                        confidence=raw.get("confidence", "verified"),
                        source=raw["source"],
                        licence=raw["licence"],
                    ),
                )
            )

    output: list[FrequencyVerb] = []
    for language in Language:
        language_rows = sorted(
            (item for item in rows if item[1].language is language),
            key=lambda item: (-item[0], item[1].lemma.casefold()),
        )
        for rank, (_, record) in enumerate(language_rows, 1):
            output.append(record.model_copy(update={"rank": rank}))
    write_frequency_jsonl(destination, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Reviewed UTF-8 TSV lemma lexicon")
    parser.add_argument("destination", type=Path, help="Output JSONL path")
    args = parser.parse_args()
    build(args.source, args.destination)


if __name__ == "__main__":
    main()
