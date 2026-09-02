from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.tts.models import TtsSettings, VoiceSettings
from easy_language_learning_tool.tts.service import TtsService
from easy_language_learning_tool.workbook.service import SENTENCE_HEADERS


class FakeAudioBackend:
    def __init__(self, fail_on_text: str | None = None) -> None:
        self.fail_on_text = fail_on_text

    async def synthesize(self, text: str, voice: VoiceSettings, output: Path) -> None:
        if text == self.fail_on_text:
            raise RuntimeError("simulated TTS failure")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"VOICE={voice.voice}:{text}".encode())

    def make_silence(self, seconds: int, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"SILENCE={seconds}".encode())

    def concatenate(self, inputs: list[Path], output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"|".join(path.read_bytes() for path in inputs))

    def convert_to_wav(self, source: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(source.read_bytes())

    def verify(self, path: Path) -> None:
        if not path.exists() or not path.read_bytes():
            raise RuntimeError("invalid audio")


def create_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sentences"
    sheet.append(SENTENCE_HEADERS)
    sheet.append(("sein", "to be", "Ich bin hier.", "I am here."))
    sheet.append(("haben", "to have", "Ich habe Zeit.", "I have time."))
    workbook.save(path)


def settings() -> TtsSettings:
    return TtsSettings(
        foreign=VoiceSettings(language=Language.GERMAN, voice="de-DE-KatjaNeural"),
        translation=VoiceSettings(language=Language.US_ENGLISH, voice="en-US-JennyNeural"),
    )


class TtsTests(unittest.TestCase):
    def test_preview_uses_exactly_two_rows_and_full_job_completes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "input.xlsx"
            create_workbook(workbook)
            service = TtsService(FakeAudioBackend())
            preview = asyncio.run(service.preview(workbook, settings(), root / "preview.mp3"))
            self.assertTrue(preview.exists())
            manifest = asyncio.run(
                service.generate(workbook, settings(), root / "job", root / "final.mp3")
            )
            self.assertEqual(manifest.state, "complete")
            self.assertEqual(manifest.completed_rows, [1, 2])

    def test_failure_preserves_last_completed_row_and_partial_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "input.xlsx"
            create_workbook(workbook)
            service = TtsService(FakeAudioBackend(fail_on_text="haben"))
            manifest = asyncio.run(
                service.generate(workbook, settings(), root / "job", root / "final.mp3")
            )
            self.assertEqual(manifest.state, "failed")
            self.assertEqual(manifest.completed_rows, [1])
            self.assertTrue(Path(manifest.partial_mp3 or "").exists())


if __name__ == "__main__":
    unittest.main()
