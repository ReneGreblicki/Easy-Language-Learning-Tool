from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from tool.configure_android_deep_link import (
    ANDROID,
    APP_LABEL,
    REQUIRED_PERMISSIONS,
    configure_manifest,
)


class ConfigureAndroidManifestTest(unittest.TestCase):
    def test_release_manifest_gets_network_permissions_and_callback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "AndroidManifest.xml"
            icon_source = root / "logo.png"
            icon_target = root / "res" / "drawable" / "app_icon.png"
            manifest.write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
                '<application><activity android:name=".MainActivity" /></application>'
                "</manifest>",
                encoding="utf-8",
            )
            icon_source.write_bytes(b"test-icon")

            configure_manifest(manifest, icon_source, icon_target)
            configure_manifest(manifest, icon_source, icon_target)

            parsed = ElementTree.parse(manifest).getroot()
            application = parsed.find("application")
            self.assertIsNotNone(application)
            self.assertEqual(application.get(f"{{{ANDROID}}}label"), APP_LABEL)
            permissions = [
                item.get(f"{{{ANDROID}}}name") for item in parsed.findall("uses-permission")
            ]
            self.assertEqual(set(permissions), set(REQUIRED_PERMISSIONS))
            self.assertEqual(len(permissions), len(REQUIRED_PERMISSIONS))
            tts_actions = [
                item.get(f"{{{ANDROID}}}name") for item in parsed.findall("queries/intent/action")
            ]
            self.assertEqual(tts_actions, ["android.intent.action.TTS_SERVICE"])
            callback = parsed.find("application/activity/intent-filter/data")
            self.assertIsNotNone(callback)
            self.assertEqual(
                callback.get(f"{{{ANDROID}}}scheme"),
                "com.renegreblicki.easylanguageflashcards",
            )
            self.assertEqual(callback.get(f"{{{ANDROID}}}host"), "login-callback")
            self.assertEqual(icon_target.read_bytes(), b"test-icon")


if __name__ == "__main__":
    unittest.main()
