from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import CefrLevel, CefrMode, GrammaticalPerson, Language, SentenceKind


class CefrSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: CefrMode
    single_level: CefrLevel | None = None
    start_level: CefrLevel | None = None
    end_level: CefrLevel | None = None
    percentages: dict[CefrLevel, Decimal] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_selection(self) -> CefrSelection:
        if self.mode is CefrMode.SINGLE:
            if self.single_level is None:
                raise ValueError("Single-level mode requires one CEFR level.")
            return self

        if self.start_level is None or self.end_level is None:
            raise ValueError("Gradual mode requires a start and end level.")
        levels = list(CefrLevel)
        start = levels.index(self.start_level)
        end = levels.index(self.end_level)
        if start > end:
            raise ValueError("The CEFR range must be in ascending order.")
        selected = levels[start : end + 1]
        if set(self.percentages) != set(selected):
            raise ValueError("Percentages must be supplied for every selected CEFR level only.")
        if any(value < 0 for value in self.percentages.values()):
            raise ValueError("CEFR percentages cannot be negative.")
        if sum(self.percentages.values()) != Decimal("100"):
            raise ValueError("CEFR percentages must total exactly 100%.")
        return self

    def ordered_levels(self) -> tuple[CefrLevel, ...]:
        if self.mode is CefrMode.SINGLE:
            assert self.single_level is not None
            return (self.single_level,)
        levels = list(CefrLevel)
        assert self.start_level is not None and self.end_level is not None
        return tuple(levels[levels.index(self.start_level) : levels.index(self.end_level) + 1])


class GenerationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    learning_language: Language
    translation_language: Language
    base_sentences: int = Field(ge=1, le=5_000)
    extra_forms: int = Field(ge=0, le=4)
    question_percentage: Decimal = Field(ge=0, le=100)
    pronoun_change: int = Field(ge=1, le=5)
    cefr: CefrSelection
    seed: int = 0

    @model_validator(mode="after")
    def validate_product_limits(self) -> GenerationSettings:
        if self.learning_language is self.translation_language:
            raise ValueError("Learning and translation languages must differ.")
        if self.final_rows > 5_000:
            raise ValueError(
                "The final output cannot exceed 5,000 rows: base words × (1 + extra forms)."
            )
        return self

    @property
    def final_rows(self) -> int:
        return self.base_sentences * (1 + self.extra_forms)


class WordRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int = Field(ge=1)
    lemma: str = Field(min_length=1)
    part_of_speech: str = Field(default="unknown", min_length=1)
    forms: tuple[str, ...] = ()
    translation: str = ""
    confidence: str = "verified"
    source: str = ""
    licence: str = ""


class PlannedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int
    base_index: int
    form_index: int
    word: WordRecord
    cefr_level: CefrLevel
    sentence_kind: SentenceKind
    grammatical_person: GrammaticalPerson
    seed: int
