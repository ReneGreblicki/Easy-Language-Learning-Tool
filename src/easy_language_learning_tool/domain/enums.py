from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    US_ENGLISH = "en-US"
    EUROPEAN_SPANISH = "es-ES"
    GERMAN = "de-DE"
    EUROPEAN_PORTUGUESE = "pt-PT"
    FRENCH = "fr-FR"
    ITALIAN = "it-IT"

    @property
    def label(self) -> str:
        return {
            self.US_ENGLISH: "US English",
            self.EUROPEAN_SPANISH: "European Spanish",
            self.GERMAN: "German",
            self.EUROPEAN_PORTUGUESE: "European Portuguese",
            self.FRENCH: "French",
            self.ITALIAN: "Italian",
        }[self]


class CefrLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


CEFR_LEVELS: tuple[CefrLevel, ...] = tuple(CefrLevel)
CEFR_MAX_WORDS: dict[CefrLevel, int] = {
    CefrLevel.A1: 5,
    CefrLevel.A2: 8,
    CefrLevel.B1: 11,
    CefrLevel.B2: 14,
    CefrLevel.C1: 17,
    CefrLevel.C2: 20,
}


class CefrMode(StrEnum):
    SINGLE = "single"
    GRADUAL = "gradual"


class SentenceKind(StrEnum):
    QUESTION = "question"
    STATEMENT = "statement"


class GrammaticalPerson(StrEnum):
    FIRST_SINGULAR = "first_singular"
    SECOND_SINGULAR = "second_singular"
    THIRD_SINGULAR = "third_singular"
    FIRST_PLURAL = "first_plural"
    SECOND_PLURAL = "second_plural"
    THIRD_PLURAL = "third_plural"


class Provider(StrEnum):
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    GEMINI = "Google Gemini"
    DEEPSEEK = "DeepSeek"
    OLLAMA = "Ollama"
    CUSTOM_COMPATIBLE = "Custom OpenAI-compatible"
