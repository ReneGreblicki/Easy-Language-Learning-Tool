from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from easy_language_learning_tool.workbook.service import WorkbookRow, import_xlsx

from .manifest import (
    TtsManifest,
    file_checksum,
    load_manifest,
    save_manifest,
    settings_checksum,
)
from .models import TtsSettings, VoiceSettings


async def list_edge_voices(language_code: str) -> list[str]:
    """Return Edge neural voice short names for one exact locale."""
    import edge_tts

    voices = await edge_tts.list_voices()
    return sorted(
        str(voice["ShortName"])
        for voice in voices
        if str(voice.get("Locale", "")).casefold() == language_code.casefold()
        and voice.get("ShortName")
    )


class AudioBackend(Protocol):
    async def synthesize(self, text: str, voice: VoiceSettings, output: Path) -> None: ...

    def make_silence(self, seconds: int, output: Path) -> None: ...

    def concatenate(self, inputs: list[Path], output: Path) -> None: ...

    def convert_to_wav(self, source: Path, output: Path) -> None: ...

    def verify(self, path: Path) -> None: ...


class EdgeFfmpegBackend:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> None:
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    async def synthesize(self, text: str, voice: VoiceSettings, output: Path) -> None:
        import edge_tts

        output.parent.mkdir(parents=True, exist_ok=True)
        communicator = edge_tts.Communicate(
            text=text,
            voice=voice.voice,
            rate=voice.edge_rate,
            pitch=voice.edge_pitch,
            volume=voice.edge_volume,
        )
        await communicator.save(str(output))

    def make_silence(self, seconds: int, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                self.ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=24000:cl=mono",
                "-t",
                str(seconds),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(output),
            ]
        )

    def concatenate(self, inputs: list[Path], output: Path) -> None:
        if not inputs:
            raise ValueError("At least one audio input is required.")
        output.parent.mkdir(parents=True, exist_ok=True)
        list_path = output.with_suffix(".concat.txt")
        lines = []
        for item in inputs:
            safe = str(item.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            self._run(
                [
                    self.ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(output),
                ]
            )
        finally:
            list_path.unlink(missing_ok=True)

    def convert_to_wav(self, source: Path, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                self.ffmpeg,
                "-y",
                "-i",
                str(source),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "44100",
                "-ac",
                "1",
                str(output),
            ]
        )

    def verify(self, path: Path) -> None:
        self._run(
            [
                self.ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ]
        )
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("The produced MP3 is empty.")

    @staticmethod
    def _run(command: list[str]) -> None:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0,
        )


class TtsService:
    def __init__(self, backend: AudioBackend) -> None:
        self.backend = backend
        self._run_event = asyncio.Event()
        self._run_event.set()
        self._cancelled = False

    def pause(self) -> None:
        self._run_event.clear()

    def resume(self) -> None:
        self._run_event.set()

    def cancel(self) -> None:
        self._cancelled = True
        self._run_event.set()

    async def preview(
        self,
        workbook_path: Path,
        settings: TtsSettings,
        output_path: Path,
    ) -> Path:
        rows = import_xlsx(workbook_path)[:2]
        work = output_path.parent / f"{output_path.stem}_preview_parts"
        row_files = await self._build_rows(rows, settings, work, range(1, len(rows) + 1), None)
        self.backend.concatenate(row_files, output_path)
        self.backend.verify(output_path)
        return output_path

    async def generate(
        self,
        workbook_path: Path,
        settings: TtsSettings,
        job_directory: Path,
        output_path: Path,
        progress: Callable[[int, int], None] | None = None,
    ) -> TtsManifest:
        rows = import_xlsx(workbook_path)
        job_directory.mkdir(parents=True, exist_ok=True)
        manifest_path = job_directory / "manifest.json"
        workbook_hash = file_checksum(workbook_path)
        settings_hash = settings_checksum(settings)
        manifest = load_manifest(manifest_path)
        if manifest is not None and (
            manifest.workbook_checksum != workbook_hash
            or manifest.settings_checksum != settings_hash
        ):
            raise ValueError("The workbook or TTS settings changed; this job cannot resume safely.")
        if manifest is None:
            manifest = TtsManifest(
                workbook_checksum=workbook_hash,
                settings_checksum=settings_hash,
                total_rows=len(rows),
                state="running",
            )
            save_manifest(manifest_path, manifest)
        self._cancelled = False
        completed = set(manifest.completed_rows)
        try:
            for row_number, row in enumerate(rows, 1):
                if row_number in completed:
                    if progress:
                        progress(len(completed), len(rows))
                    continue
                await self._run_event.wait()
                if self._cancelled:
                    break
                await self._build_rows([row], settings, job_directory, [row_number], None)
                completed.add(row_number)
                manifest = manifest.model_copy(
                    update={
                        "completed_rows": sorted(completed),
                        "state": "running",
                        "last_error": None,
                    }
                )
                save_manifest(manifest_path, manifest)
                if progress:
                    progress(len(completed), len(rows))

            row_files = [
                job_directory / "rows" / f"{number:05d}.mp3" for number in sorted(completed)
            ]
            partial = job_directory / "partial.mp3"
            if row_files:
                self.backend.concatenate(row_files, partial)
                self.backend.verify(partial)
            if self._cancelled or len(completed) != len(rows):
                manifest = manifest.model_copy(
                    update={
                        "state": "cancelled",
                        "partial_mp3": str(partial) if partial.exists() else None,
                    }
                )
            else:
                shutil.copy2(partial, output_path)
                self.backend.verify(output_path)
                manifest = manifest.model_copy(
                    update={
                        "state": "complete",
                        "partial_mp3": str(partial),
                        "final_mp3": str(output_path),
                    }
                )
            save_manifest(manifest_path, manifest)
            return manifest
        except Exception as error:
            completed_files = [
                job_directory / "rows" / f"{number:05d}.mp3" for number in sorted(completed)
            ]
            partial = job_directory / "partial.mp3"
            if completed_files:
                self.backend.concatenate(completed_files, partial)
            failed = manifest.model_copy(
                update={
                    "completed_rows": sorted(completed),
                    "state": "failed",
                    "last_error": str(error),
                    "partial_mp3": str(partial) if partial.exists() else None,
                }
            )
            save_manifest(manifest_path, failed)
            return failed

    async def _build_rows(
        self,
        rows: list[WorkbookRow],
        settings: TtsSettings,
        work_directory: Path,
        row_numbers: range | list[int],
        progress: Callable[[int, int], None] | None,
    ) -> list[Path]:
        silence_directory = work_directory / "silence"
        clip_directory = work_directory / "cells"
        row_directory = work_directory / "rows"
        silences: list[Path] = []
        for seconds in settings.pauses:
            silence = silence_directory / f"pause_{seconds}s.mp3"
            if not silence.exists() or silence.stat().st_size == 0:
                self.backend.make_silence(seconds, silence)
            silences.append(silence)
        row_files: list[Path] = []
        for index, (number, row) in enumerate(zip(row_numbers, rows, strict=True), 1):
            output = row_directory / f"{number:05d}.mp3"
            if output.exists() and output.stat().st_size > 0:
                row_files.append(output)
                continue
            values = (
                (row.foreign_word, settings.foreign),
                (row.word_translation, settings.translation),
                (row.foreign_sentence, settings.foreign),
                (row.sentence_translation, settings.translation),
            )
            pieces: list[Path] = []
            for column, ((text, voice), silence) in enumerate(
                zip(values, silences, strict=True), 1
            ):
                clip = clip_directory / f"{number:05d}_{column}.mp3"
                if not clip.exists() or clip.stat().st_size == 0:
                    await self.backend.synthesize(text, voice, clip)
                pieces.extend((clip, silence))
            self.backend.concatenate(pieces, output)
            self.backend.verify(output)
            row_files.append(output)
            if progress:
                progress(index, len(rows))
        return row_files
