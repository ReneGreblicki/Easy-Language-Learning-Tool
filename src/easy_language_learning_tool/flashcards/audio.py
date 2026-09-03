from __future__ import annotations

import hashlib
from pathlib import Path

from easy_language_learning_tool.tts.manifest import file_checksum
from easy_language_learning_tool.tts.models import VoiceSettings
from easy_language_learning_tool.tts.service import AudioBackend


class FlashcardAudioService:
    """Reuse TTS cell clips and lazily cache any flashcard audio that is missing."""

    def __init__(self, cache_root: Path, backend: AudioBackend) -> None:
        self.cache_root = cache_root
        self.backend = backend

    async def prepare(
        self,
        workbook: Path,
        rank: int,
        cells: tuple[tuple[int, str], ...],
        voice: VoiceSettings,
    ) -> Path:
        if not cells:
            raise ValueError("At least one flashcard cell is required for audio playback.")
        clips = [
            await self._cell_clip(workbook, rank, column, text, voice) for column, text in cells
        ]
        if len(clips) == 1:
            return clips[0]
        digest = hashlib.sha256()
        for clip in clips:
            digest.update(clip.read_bytes())
        output = self.cache_root / "flashcards" / "audio" / f"combined-{digest.hexdigest()}.mp3"
        if not self._usable(output):
            self.backend.concatenate(clips, output)
            self.backend.verify(output)
        return output

    async def prepare_playback(
        self,
        workbook: Path,
        rank: int,
        cells: tuple[tuple[int, str], ...],
        voice: VoiceSettings,
    ) -> Path:
        """Return a native-playback WAV, transcoding only once per cached clip."""
        source = await self.prepare(workbook, rank, cells, voice)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        output = self.cache_root / "flashcards" / "playback" / f"{digest}.wav"
        if not self._usable(output):
            self.backend.convert_to_wav(source, output)
            self.backend.verify(output)
        return output

    async def _cell_clip(
        self,
        workbook: Path,
        rank: int,
        column: int,
        text: str,
        voice: VoiceSettings,
    ) -> Path:
        reusable = self._existing_tts_clip(workbook, rank, column)
        if reusable is not None:
            return reusable
        key = hashlib.sha256(f"{text}\0{voice.model_dump_json()}".encode()).hexdigest()
        output = self.cache_root / "flashcards" / "audio" / f"cell-{key}.mp3"
        if not self._usable(output):
            await self.backend.synthesize(text, voice, output)
            self.backend.verify(output)
        return output

    def _existing_tts_clip(self, workbook: Path, rank: int, column: int) -> Path | None:
        prefix = file_checksum(workbook)[:12]
        pattern = f"{prefix}-*/cells/{rank:05d}_{column}.mp3"
        candidates = [
            path for path in (self.cache_root / "tts" / "jobs").glob(pattern) if self._usable(path)
        ]
        return max(candidates, key=lambda path: path.stat().st_mtime_ns, default=None)

    @staticmethod
    def _usable(path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0
