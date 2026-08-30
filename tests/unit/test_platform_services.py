from __future__ import annotations

import asyncio
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from easy_language_learning_tool.config import paths as path_module
from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.security.credentials import CredentialStore
from easy_language_learning_tool.tts.models import VoiceSettings
from easy_language_learning_tool.tts.service import EdgeFfmpegBackend, list_edge_voices


class PlatformServiceTests(unittest.TestCase):
    def test_app_paths_fallback_and_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with (
                patch.object(path_module, "PlatformDirs", None),
                patch.object(path_module.Path, "home", return_value=home),
            ):
                paths = path_module.resolve_app_paths()
                paths.create()
            self.assertTrue(paths.data.is_dir())
            self.assertTrue(paths.history.is_dir())

    def test_app_paths_platformdirs_branch(self) -> None:
        class FakeDirs:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                self.user_data_dir = "/tmp/app-data"
                self.user_cache_dir = "/tmp/app-cache"
                self.user_log_dir = "/tmp/app-logs"

        with patch.object(path_module, "PlatformDirs", FakeDirs):
            paths = path_module.resolve_app_paths()
        self.assertEqual(paths.data, Path("/tmp/app-data"))

    def test_credential_store_session_and_keyring(self) -> None:
        values: dict[tuple[str, str], str] = {}
        fake = types.SimpleNamespace(
            set_password=lambda service, provider, value: values.__setitem__(
                (service, provider), value
            ),
            get_password=lambda service, provider: values.get((service, provider)),
            delete_password=lambda service, provider: values.pop((service, provider)),
        )
        with patch.dict(sys.modules, {"keyring": fake}):
            store = CredentialStore()
            store.set("OpenAI", "secret", remember=True)
            self.assertEqual(store.get("OpenAI"), "secret")
            store.session_values.clear()
            self.assertEqual(store.get("OpenAI"), "secret")
            store.delete("OpenAI")
            self.assertIsNone(store.get("OpenAI"))
            store.set("OpenAI", "temporary", remember=False)
            store.set("OpenAI", "", remember=False)
            self.assertIsNone(store.get("OpenAI"))

    def test_credential_store_normalizes_save_failure(self) -> None:
        def fail(*_args: object) -> None:
            raise RuntimeError("backend unavailable")

        fake = types.SimpleNamespace(set_password=fail)
        with (
            patch.dict(sys.modules, {"keyring": fake}),
            self.assertRaisesRegex(RuntimeError, "Windows Credential Manager"),
        ):
            CredentialStore().set("OpenAI", "secret", remember=True)

    def test_edge_backend_synthesis_and_file_operations(self) -> None:
        class FakeCommunicate:
            def __init__(self, **_kwargs: object) -> None:
                pass

            async def save(self, path: str) -> None:
                Path(path).write_bytes(b"audio")

        fake_edge_tts = types.SimpleNamespace(Communicate=FakeCommunicate)
        voice = VoiceSettings(language=Language.GERMAN, voice="de-DE-KatjaNeural")
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(sys.modules, {"edge_tts": fake_edge_tts}),
        ):
            root = Path(directory)
            backend = EdgeFfmpegBackend("ffmpeg-test", "ffprobe-test")
            clip = root / "cells" / "clip.mp3"
            asyncio.run(backend.synthesize("Guten Tag", voice, clip))
            self.assertEqual(clip.read_bytes(), b"audio")

            commands: list[list[str]] = []

            def fake_run(command: list[str]) -> None:
                commands.append(command)
                Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
                Path(command[-1]).write_bytes(b"output")

            backend._run = fake_run  # type: ignore[method-assign]
            silence = root / "silence.mp3"
            backend.make_silence(2, silence)
            combined = root / "combined.mp3"
            backend.concatenate([clip, silence], combined)
            backend.verify(combined)
            self.assertGreaterEqual(len(commands), 3)
            self.assertFalse(combined.with_suffix(".concat.txt").exists())

    def test_edge_backend_run_invokes_subprocess(self) -> None:
        with patch("subprocess.run") as run:
            EdgeFfmpegBackend._run(["ffprobe", "file.mp3"])
        run.assert_called_once()

    def test_edge_voice_discovery_filters_exact_locale(self) -> None:
        async def voices() -> list[dict[str, str]]:
            return [
                {"Locale": "de-DE", "ShortName": "de-DE-KatjaNeural"},
                {"Locale": "de-AT", "ShortName": "de-AT-IngridNeural"},
                {"Locale": "de-DE", "ShortName": "de-DE-ConradNeural"},
            ]

        with patch.dict(sys.modules, {"edge_tts": types.SimpleNamespace(list_voices=voices)}):
            result = asyncio.run(list_edge_voices("de-DE"))
        self.assertEqual(result, ["de-DE-ConradNeural", "de-DE-KatjaNeural"])

    def test_thai_script_variants_use_the_native_voice_locale(self) -> None:
        self.assertEqual(Language.THAI_SCRIPT.speech_locale, "th-TH")
        self.assertEqual(Language.THAI_PAIBOON.speech_locale, "th-TH")


if __name__ == "__main__":
    unittest.main()
