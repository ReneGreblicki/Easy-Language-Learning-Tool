from __future__ import annotations

import gzip
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .enums import Language
from .models import WordRecord


class FrequencyWord(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: Language
    rank: int = Field(ge=1)
    lemma: str = Field(min_length=1)
    part_of_speech: str = Field(min_length=1)
    forms: tuple[str, ...] = ()
    translations: dict[Language, str]
    confidence: str = "verified"
    source: str
    licence: str
    source_url: str = ""
    source_revision: str = ""
    validation_status: str = "automated"


class FrequencyRepository:
    def __init__(self, records: list[FrequencyWord]) -> None:
        self._records = records

    @property
    def records(self) -> tuple[FrequencyWord, ...]:
        return tuple(self._records)

    @classmethod
    def from_jsonl(cls, path: Path) -> FrequencyRepository:
        records: list[FrequencyWord] = []
        opener = gzip.open if path.suffix.casefold() == ".gz" else Path.open
        with opener(path, mode="rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try:
                        records.append(FrequencyWord.model_validate_json(line))
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
    ) -> list[WordRecord]:
        candidates = sorted(
            (record for record in self._records if record.language is language),
            key=lambda record: (record.rank, record.lemma.casefold()),
        )
        seen: set[str] = set()
        selected: list[WordRecord] = []
        for record in candidates:
            normalized = record.lemma.casefold().strip()
            translation = record.translations.get(translation_language, "").strip()
            if normalized in seen:
                continue
            selected.append(
                WordRecord(
                    rank=record.rank,
                    lemma=record.lemma,
                    part_of_speech=record.part_of_speech,
                    forms=record.forms,
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
            f"Only {len(selected)} unique ranked words are available for {language.label}; "
            f"{count} requested."
        )

    def available_count(self, language: Language, translation_language: Language) -> int:
        return len(
            {
                record.lemma.casefold().strip()
                for record in self._records
                if record.language is language
            }
        )

    def validate_release_readiness(self, minimum_per_language: int = 5_000) -> list[str]:
        errors: list[str] = []
        for language in Language:
            records = sorted(
                (record for record in self._records if record.language is language),
                key=lambda record: (record.rank, record.lemma.casefold()),
            )
            unique = {record.lemma.casefold().strip() for record in records}
            issues: list[str] = []
            if len(unique) < minimum_per_language:
                issues.append(f"{len(unique)} ranked words; {minimum_per_language} required")
            if len(unique) != len(records):
                issues.append("duplicate words are present")
            if [record.rank for record in records] != list(range(1, len(records) + 1)):
                issues.append("ranks must be unique and contiguous from 1")
            if any(not record.source or not record.licence for record in records):
                issues.append("source or licence metadata is missing")
            if any(not record.source_url or not record.source_revision for record in records):
                issues.append("source URL or source revision is missing")
            if any(not record.part_of_speech.strip() for record in records):
                issues.append("part of speech is missing")
            if any(record.validation_status != "automated" for record in records):
                issues.append("one or more records did not pass the automated corpus pipeline")
            if issues:
                errors.append(f"{language.label}: {'; '.join(issues)}.")
        return errors


def write_frequency_jsonl(path: Path, records: list[FrequencyWord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix.casefold() == ".gz" else Path.open
    with opener(path, mode="wt", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n")
