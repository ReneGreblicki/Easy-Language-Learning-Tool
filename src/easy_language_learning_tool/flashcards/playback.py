from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


class FlashcardAudioPlayer:
    """Replay cached WAV files through the native Windows audio service."""

    def __init__(self, sound_api: Any | None = None) -> None:
        if sound_api is None and sys.platform == "win32":
            import winsound

            sound_api = winsound
        self._sound_api = sound_api

    def play(self, path: Path) -> None:
        if self._sound_api is None:
            raise RuntimeError("Flashcard audio playback requires Windows.")
        if not path.is_file() or path.suffix.casefold() != ".wav":
            raise ValueError("Flashcard audio must be an available WAV file.")
        self.stop()
        flags = (
            self._sound_api.SND_FILENAME | self._sound_api.SND_ASYNC | self._sound_api.SND_NODEFAULT
        )
        self._sound_api.PlaySound(str(path), flags)

    def stop(self) -> None:
        if self._sound_api is not None:
            self._sound_api.PlaySound(None, 0)
