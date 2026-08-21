from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language

REQUIRED_COLUMNS = {
    "language",
    "lemma",
    "en-US",
    "es-ES",
    "de-DE",
    "pt-PT",
    "fr-FR",
    "supported_constructions",
    "source",
    "licence",
    "source_url",
    "source_revision",
    "review_status",
    "reviewer",
    "reviewed_at",
}


def audit(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    summaries: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            return [f"Missing columns: {', '.join(sorted(missing_columns))}."], []
        rows = list(reader)

    for language in Language:
        language_rows = [row for row in rows if row["language"] == language.value]
        normalized = [row["lemma"].casefold().strip() for row in language_rows]
        duplicate_count = sum(count - 1 for count in Counter(normalized).values() if count > 1)
        approved = [row for row in language_rows if row["review_status"] == "approved"]
        translated = [
            row
            for row in language_rows
            if all(row[target.value].strip() for target in Language if target is not language)
        ]
        flagged = [
            row
            for row in language_rows
            if row.get("usage_flags", "").strip() or row.get("locale_flags", "").strip()
        ]
        summaries.append(
            f"{language.label}: {len(language_rows):,} candidates; {len(translated):,} fully "
            f"translated; {len(approved):,} approved; {len(flagged):,} flagged; "
            f"{duplicate_count:,} duplicates."
        )
        if duplicate_count:
            errors.append(f"{language.label}: {duplicate_count} duplicate lemmas.")
        if any(
            row["review_status"] == "approved" and not row["reviewer"].strip() for row in approved
        ):
            errors.append(f"{language.label}: approved rows without a reviewer.")
        if any(
            row["review_status"] == "approved"
            and any(not row[target.value].strip() for target in Language if target is not language)
            for row in approved
        ):
            errors.append(f"{language.label}: approved rows with missing translations.")
    return errors, summaries


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the human-review frequency TSV.")
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    errors, summaries = audit(arguments.path)
    for summary in summaries:
        print(summary)
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
