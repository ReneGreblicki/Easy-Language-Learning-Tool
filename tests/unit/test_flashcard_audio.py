from __future__ import annotations

import asyncio
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.flashcards.audio import FlashcardAudioService
from easy_language_learning_tool.tts.manifest import file_checksum
from easy_language_learning_tool.tts.models import VoiceSettings


class FakeAudioBackend:
    def __init__(self) -> None:
        self.synthesized: list[str] = []
        self.concatenated: list[list[Path]] = []

    async def synthesize(self, text: str, voice: VoiceSettings, output: Path) -> None:
        self.synthesized.append(text)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text.encode())

    def make_silence(self, seconds: int, output: Path) -> None:
        raise AssertionError("Flashcard audio must not create TTS row pauses.")

    def concatenate(self, inputs: list[Path], output: Path) -> None:
        self.concatenated.append(inputs)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"|".join(item.read_bytes() for item in inputs))

    def verify(self, path: Path) -> None:
        assert path.is_file() and path.stat().st_size > 0


def test_reuses_individual_tts_cell_clip(tmp_path: Path) -> None:
    workbook = tmp_path / "cards.xlsx"
    workbook.write_bytes(b"workbook")
    prefix = file_checksum(workbook)[:12]
    existing = tmp_path / "cache" / "tts" / "jobs" / f"{prefix}-settings" / "cells"
    existing.mkdir(parents=True)
    clip = existing / "00003_1.mp3"
    clip.write_bytes(b"existing")
    backend = FakeAudioBackend()
    service = FlashcardAudioService(tmp_path / "cache", backend)
    voice = VoiceSettings(language=Language.EUROPEAN_SPANISH, voice="test-voice")

    result = asyncio.run(service.prepare(workbook, 3, ((1, "palabra"),), voice))

    assert result == clip
    assert backend.synthesized == []


def test_lazily_caches_word_and_sentence_as_one_playback(tmp_path: Path) -> None:
    workbook = tmp_path / "cards.xlsx"
    workbook.write_bytes(b"workbook")
    backend = FakeAudioBackend()
    service = FlashcardAudioService(tmp_path / "cache", backend)
    voice = VoiceSettings(language=Language.US_ENGLISH, voice="test-voice")
    cells = ((2, "tool"), (4, "The tool is useful."))

    first = asyncio.run(service.prepare(workbook, 1, cells, voice))
    second = asyncio.run(service.prepare(workbook, 1, cells, voice))

    assert first == second
    assert first.read_bytes() == b"tool|The tool is useful."
    assert backend.synthesized == ["tool", "The tool is useful."]
    assert len(backend.concatenated) == 1
