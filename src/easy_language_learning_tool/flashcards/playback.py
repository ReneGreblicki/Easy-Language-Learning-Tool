from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


class FlashcardAudioPlayer:
    """Replay cached WAV files through the native desktop audio service."""

    def __init__(
        self,
        sound_api: Any | None = None,
        process_factory: Any | None = None,
        platform_name: str | None = None,
    ) -> None:
        self._platform = platform_name or sys.platform
        if sound_api is None and sys.platform == "win32":
            import winsound

            sound_api = winsound
        self._sound_api = sound_api
        self._process_factory = process_factory or subprocess.Popen
        self._process: Any | None = None

    def play(self, path: Path) -> None:
        if not path.is_file() or path.suffix.casefold() != ".wav":
            raise ValueError("Flashcard audio must be an available WAV file.")
        self.stop()
        if self._platform == "win32" and self._sound_api is not None:
            flags = (
                self._sound_api.SND_FILENAME
                | self._sound_api.SND_ASYNC
                | self._sound_api.SND_NODEFAULT
            )
            self._sound_api.PlaySound(str(path), flags)
            return
        if self._platform == "darwin":
            self._process = self._process_factory(
                ["/usr/bin/afplay", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        raise RuntimeError("Flashcard audio playback requires Windows or macOS.")

    def stop(self) -> None:
        if self._sound_api is not None:
            self._sound_api.PlaySound(None, 0)
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
            self._process = None
