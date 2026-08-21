from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from easy_language_learning_tool.domain.enums import Language


class VoiceSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: Language
    voice: str = Field(min_length=1)
    rate: int = Field(default=0, ge=-100, le=100)
    pitch_hz: int = Field(default=0, ge=-100, le=100)
    volume: int = Field(default=0, ge=-100, le=100)

    @property
    def edge_rate(self) -> str:
        return f"{self.rate:+d}%"

    @property
    def edge_pitch(self) -> str:
        return f"{self.pitch_hz:+d}Hz"

    @property
    def edge_volume(self) -> str:
        return f"{self.volume:+d}%"


class TtsSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    foreign: VoiceSettings
    translation: VoiceSettings
    pause_after_foreign_verb: int = Field(default=1, ge=1, le=10)
    pause_after_verb_translation: int = Field(default=1, ge=1, le=10)
    pause_after_foreign_sentence: int = Field(default=2, ge=1, le=10)
    pause_after_sentence_translation: int = Field(default=2, ge=1, le=10)

    @property
    def pauses(self) -> tuple[int, int, int, int]:
        return (
            self.pause_after_foreign_verb,
            self.pause_after_verb_translation,
            self.pause_after_foreign_sentence,
            self.pause_after_sentence_translation,
        )
