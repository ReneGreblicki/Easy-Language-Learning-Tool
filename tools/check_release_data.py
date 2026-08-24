from __future__ import annotations

import argparse
from pathlib import Path

from easy_language_learning_tool.domain.frequency import FrequencyRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate production frequency-data coverage.")
    parser.add_argument("path", type=Path, help="Combined frequency JSONL file")
    parser.add_argument("--minimum", type=int, default=5_000)
    arguments = parser.parse_args()
    errors = FrequencyRepository.from_jsonl(arguments.path).validate_release_readiness(
        arguments.minimum
    )
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Frequency data is release-ready at {arguments.minimum:,} words per language.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
