from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = 1


class SyncOperationType(StrEnum):
    UPSERT = "upsert"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"


class CardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    rank: int = Field(ge=1, le=5000)
    foreign_word: str = Field(min_length=1)
    word_translation: str = Field(min_length=1)
    foreign_sentence: str = Field(min_length=1)
    sentence_translation: str = Field(min_length=1)
    revision: int = Field(default=1, ge=1)


class DeckPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: int = CONTRACT_VERSION
    id: UUID
    title: str = Field(min_length=1, max_length=200)
    source_language: str = Field(min_length=2)
    translation_language: str = Field(min_length=2)
    cefr_level: str | None = None
    settings: dict[str, object] = Field(default_factory=dict)
    cards: list[CardPayload] = Field(min_length=1, max_length=5000)
    revision: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_unique_card_ranks(self) -> DeckPayload:
        ranks = [card.rank for card in self.cards]
        if len(ranks) != len(set(ranks)):
            raise ValueError("A synchronized deck cannot contain duplicate ranks.")
        return self


class SyncOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: int = CONTRACT_VERSION
    id: UUID
    entity_type: str
    entity_id: UUID
    operation: SyncOperationType
    payload: dict[str, object]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_deletion_payload(self) -> SyncOperation:
        if self.operation is SyncOperationType.SOFT_DELETE:
            if self.entity_type != "deck":
                raise ValueError("Only deck-wide deletion is supported.")
            if not bool(self.payload.get("delete_everywhere")):
                raise ValueError("Phone-only removal must not be represented as a sync deletion.")
        return self
