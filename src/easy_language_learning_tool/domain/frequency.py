from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

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
    source_url: str = ""
    source_revision: str = ""
    review_status: Literal["candidate", "approved"] = "candidate"
    reviewer: str = ""
    reviewed_at: str = ""


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
            translation = record.translations.get(translation_language, "").strip()
            if normalized in seen or not translation:
                continue
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
            f"Only {len(selected)} unique verbs with {translation_language.label} translations are "
            f"available for {language.label}; {count} requested."
        )

    def available_count(self, language: Language, translation_language: Language) -> int:
        return len(
            {
                record.lemma.casefold().strip()
                for record in self._records
                if record.language is language
                and bool(record.translations.get(translation_language, "").strip())
            }
        )

    def validate_release_readiness(self, minimum_per_language: int = 4_000) -> list[str]:
        errors: list[str] = []
        for language in Language:
            records = sorted(
                (record for record in self._records if record.language is language),
                key=lambda record: (record.rank, record.lemma.casefold()),
            )
            unique = {record.lemma.casefold().strip() for record in records}
            issues: list[str] = []
            if len(unique) < minimum_per_language:
                issues.append(f"{len(unique)} unique verbs; {minimum_per_language} required")
            if len(unique) != len(records):
                issues.append("duplicate lemmas are present")
            if [record.rank for record in records] != list(range(1, len(records) + 1)):
                issues.append("ranks must be unique and contiguous from 1")
            required_translations = set(Language) - {language}
            if any(
                any(
                    not record.translations.get(target, "").strip()
                    for target in required_translations
                )
                for record in records
            ):
                issues.append("one or more required translations are missing")
            if any(not record.source or not record.licence for record in records):
                issues.append("source or licence metadata is missing")
            if any(not record.source_url or not record.source_revision for record in records):
                issues.append("source URL or source revision is missing")
            if any(record.review_status != "approved" for record in records):
                issues.append("one or more records are not approved")
            if any(not record.reviewer or not record.reviewed_at for record in records):
                issues.append("reviewer or review date is missing")
            if any(not record.supported_constructions for record in records):
                issues.append("supported constructions are missing")
            if issues:
                errors.append(f"{language.label}: {'; '.join(issues)}.")
        return errors


def write_frequency_jsonl(path: Path, records: list[FrequencyVerb]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")
