"""Audit generated default-deck JSON without publishing it."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

EXPECTED_SCRIPTS = {
    "zh-CN": re.compile(r"[\u3400-\u9fff]"),
    "ml-IN": re.compile(r"[\u0d00-\u0d7f]"),
    "ru-RU": re.compile(r"[\u0400-\u04ff]"),
    "ko-KR": re.compile(r"[\uac00-\ud7af]"),
    "ja-JP": re.compile(r"[\u3040-\u30ff\u3400-\u9fff]"),
    "th-Thai-TH": re.compile(r"[\u0e00-\u0e7f]"),
}
THAI = re.compile(r"[\u0e00-\u0e7f]")
TONE_MARKS = {"\u0300", "\u0301", "\u0302", "\u030c"}


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def audit(path: Path, expected_codes: set[str] | None = None) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    languages = data["languages"]
    errors: list[str] = []
    warnings: list[str] = []
    if expected_codes is not None and set(languages) != expected_codes:
        errors.append(
            f"language set differs: missing={sorted(expected_codes - set(languages))}, "
            f"extra={sorted(set(languages) - expected_codes)}"
        )

    english = {row["id"]: row for row in languages.get("en-US", [])}
    expected_ids = set(english)
    summary: dict[str, dict[str, object]] = {}
    for code, rows in languages.items():
        ids = [row["id"] for row in rows]
        levels = Counter(row["level"] for row in rows)
        if len(ids) != len(set(ids)):
            errors.append(f"{code}: duplicate concept IDs")
        if set(ids) != expected_ids:
            errors.append(f"{code}: concept IDs differ from English")
        expected_levels = (
            {"A1": 10, "A2": 10, "B1": 10}
            if data["pilot"]
            else {
                "A1": 400,
                "A2": 300,
                "B1": 300,
            }
        )
        if dict(levels) != expected_levels:
            errors.append(f"{code}: level counts {dict(levels)} != {expected_levels}")
        if len({normalized(row["sentence"]) for row in rows}) != len(rows):
            errors.append(f"{code}: duplicate sentences")

        missing_script = 0
        pattern = EXPECTED_SCRIPTS.get(code)
        if pattern:
            missing_script = sum(
                not pattern.search(row["word"]) or not pattern.search(row["sentence"])
                for row in rows
            )
            if missing_script:
                errors.append(f"{code}: {missing_script} rows lack the expected script")

        if code == "th-Latn-TH":
            mixed = sum(THAI.search(row["word"] + row["sentence"]) is not None for row in rows)
            missing_tones = sum(
                not any(
                    mark in unicodedata.normalize("NFD", row["sentence"]) for mark in TONE_MARKS
                )
                for row in rows
            )
            if mixed:
                errors.append(f"{code}: {mixed} rows contain Thai script")
            if missing_tones:
                errors.append(f"{code}: {missing_tones} rows lack tone marks")

        sense_drift = 0
        absent_headwords = 0
        if code != "en-US":
            sense_drift = sum(
                normalized(row["sense"]) != normalized(english[row["id"]]["sense"])
                for row in rows
                if row["id"] in english
            )
            absent_headwords = sum(
                normalized(row["word"]) not in normalized(row["sentence"]) for row in rows
            )
            if sense_drift:
                errors.append(f"{code}: {sense_drift} English meanings drifted")
            if absent_headwords:
                warnings.append(
                    f"{code}: manually inspect {absent_headwords} headwords absent verbatim "
                    "from their sentences (inflection may be valid)"
                )

        summary[code] = {
            "rows": len(rows),
            "rank_matches": sum(row.get("source_rank") is not None for row in rows),
            "absent_headwords": absent_headwords,
            "sense_drift": sense_drift,
            "missing_script": missing_script,
        }

    return {"errors": errors, "warnings": warnings, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--language-codes", type=Path)
    args = parser.parse_args()
    expected = None
    if args.language_codes:
        expected = set(json.loads(args.language_codes.read_text(encoding="utf-8")))
    result = audit(args.curriculum, expected)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
