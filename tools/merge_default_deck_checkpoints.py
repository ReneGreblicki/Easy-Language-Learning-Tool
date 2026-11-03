"""Merge resumable default-deck checkpoints without replacing newer files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

BATCH_FILE = re.compile(r"^([a-z]{2}(?:-[A-Za-z]+){1,2})-[0-9a-f]{20}\.json$")


def checkpoint_inventory(directory: Path) -> dict[str, object]:
    ids_by_language: dict[str, set[int]] = defaultdict(set)
    evidence_by_language: dict[str, set[int]] = defaultdict(set)
    for path in directory.glob("*.json"):
        match = BATCH_FILE.fullmatch(path.name.replace(".evidence", ""))
        if not match:
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rows, list):
            continue
        target = evidence_by_language if path.name.endswith(".evidence.json") else ids_by_language
        target[match.group(1)].update(
            int(row["id"])
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("id"), int)
        )
    return {
        "raw_rows": sum(len(ids) for ids in ids_by_language.values()),
        "languages": {
            code: {
                "rows": len(ids),
                "evidence_rows": len(evidence_by_language.get(code, set())),
            }
            for code, ids in sorted(ids_by_language.items())
        },
    }


def merge_checkpoints(destination: Path, sources: list[Path]) -> dict[str, object]:
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    collisions = 0
    for source in sources:
        if not source.is_dir():
            raise ValueError(f"Checkpoint source does not exist: {source}")
        for path in sorted(source.iterdir()):
            if not path.is_file():
                continue
            target = destination / path.name
            if target.exists():
                collisions += 1
                continue
            shutil.copy2(path, target)
            copied += 1
    return {"copied_files": copied, "preserved_collisions": collisions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--minimum-raw-rows", type=int, default=0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    merge_report = merge_checkpoints(args.destination, args.source)
    report = {**merge_report, **checkpoint_inventory(args.destination)}
    if report["raw_rows"] < args.minimum_raw_rows:
        raise SystemExit(
            "Merged checkpoint coverage is below the paid-run safety floor: "
            f"{report['raw_rows']} < {args.minimum_raw_rows}"
        )
    content = json.dumps(report, indent=2, sort_keys=True)
    print(content)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
