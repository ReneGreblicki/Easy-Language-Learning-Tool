from __future__ import annotations

from pathlib import Path

from easy_language_learning_tool.flashcards.playback import FlashcardAudioPlayer


class FakeSoundApi:
    SND_FILENAME = 1
    SND_ASYNC = 2
    SND_NODEFAULT = 4

    def __init__(self) -> None:
        self.calls: list[tuple[str | None, int]] = []

    def PlaySound(self, path: str | None, flags: int) -> None:  # noqa: N802 - Windows API
        self.calls.append((path, flags))


def test_player_restarts_same_side_every_time(tmp_path: Path) -> None:
    clip = tmp_path / "clip.wav"
    clip.write_bytes(b"RIFF-test")
    sound_api = FakeSoundApi()
    player = FlashcardAudioPlayer(sound_api)

    player.play(clip)
    player.play(clip)

    plays = [call for call in sound_api.calls if call[0] == str(clip)]
    stops = [call for call in sound_api.calls if call[0] is None]
    assert len(plays) == 2
    assert len(stops) == 2
