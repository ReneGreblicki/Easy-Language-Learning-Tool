from __future__ import annotations

from enum import StrEnum


class Language(StrEnum):
    US_ENGLISH = "en-US"
    EUROPEAN_SPANISH = "es-ES"
    GERMAN = "de-DE"
    EUROPEAN_PORTUGUESE = "pt-PT"
    FRENCH = "fr-FR"
    ITALIAN = "it-IT"
    THAI_SCRIPT = "th-Thai-TH"
    THAI_PAIBOON = "th-Latn-TH"

    @property
    def label(self) -> str:
        return {
            self.US_ENGLISH: "US English",
            self.EUROPEAN_SPANISH: "European Spanish",
            self.GERMAN: "German",
            self.EUROPEAN_PORTUGUESE: "European Portuguese",
            self.FRENCH: "French",
            self.ITALIAN: "Italian",
            self.THAI_SCRIPT: "Thai (Thai script)",
            self.THAI_PAIBOON: "Thai (Paiboon romanization)",
        }[self]

    @property
    def speech_locale(self) -> str:
        if self in {self.THAI_SCRIPT, self.THAI_PAIBOON}:
            return "th-TH"
        return self.value

    @property
    def generation_instruction(self) -> str:
        if self is self.THAI_SCRIPT:
            return "Write Thai words and sentences only in standard Thai script."
        if self is self.THAI_PAIBOON:
            return (
                "Write Thai words and sentences only in tone-marked Paiboon romanization; "
                "do not use Thai script in the learning-language fields."
            )
        return ""


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
    NEUTRAL = "neutral"
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
