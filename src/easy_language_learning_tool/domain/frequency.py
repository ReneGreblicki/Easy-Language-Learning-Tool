from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .enums import Language
from .models import VerbRecord


class FrequencyVerb(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: Language
    rank: int = Field(ge=1)
    lemma: str = Field(min_length=1)
    translations: dict[Language, str]
    irregularity: str = "unknown"
    supported_constructions: tuple[str, ...] = ()
    confidence: str = "verified"
    source: str
    licence: str


class FrequencyRepository:
    def __init__(self, records: list[FrequencyVerb]) -> None:
        self._records = records

    @classmethod
    def from_jsonl(cls, path: Path) -> FrequencyRepository:
        records: list[FrequencyVerb] = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try:
                        records.append(FrequencyVerb.model_validate_json(line))
                    except Exception as error:
                        raise ValueError(
                            f"Invalid frequency data at line {line_number}."
                        ) from error
        return cls(records)

    def select(
        self,
        language: Language,
        translation_language: Language,
        count: int,
    ) -> list[VerbRecord]:
        candidates = sorted(
            (record for record in self._records if record.language is language),
            key=lambda record: (record.rank, record.lemma.casefold()),
        )
        seen: set[str] = set()
        selected: list[VerbRecord] = []
        for record in candidates:
            normalized = record.lemma.casefold().strip()
            if normalized in seen:
                continue
            translation = record.translations.get(translation_language, "")
            selected.append(
                VerbRecord(
                    rank=record.rank,
                    lemma=record.lemma,
                    translation=translation,
                    confidence=record.confidence,
                    source=record.source,
                    licence=record.licence,
                )
            )
            seen.add(normalized)
            if len(selected) == count:
                return selected
        raise ValueError(
            f"Only {len(selected)} unique verbs are available for {language.label}; {count} requested."
        )

    def validate_release_readiness(self, minimum_per_language: int = 4_000) -> list[str]:
        errors: list[str] = []
        for language in Language:
            records = [record for record in self._records if record.language is language]
            unique = {record.lemma.casefold().strip() for record in records}
            if len(unique) < minimum_per_language:
                errors.append(
                    f"{language.label}: {len(unique)} unique verbs; {minimum_per_language} required."
                )
            if any(not record.source or not record.licence for record in records):
                errors.append(f"{language.label}: missing source or licence metadata.")
        return errors


def write_frequency_jsonl(path: Path, records: list[FrequencyVerb]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")
