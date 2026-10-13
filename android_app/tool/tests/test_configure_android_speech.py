import tempfile
import unittest
from pathlib import Path
from tool.configure_android_speech import configure_speech


class ConfigureSpeechTests(unittest.TestCase):
    def test_registers_native_bridge_once_and_preserves_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = root / "kotlin" / "com" / "example" / "MainActivity.kt"
            activity.parent.mkdir(parents=True)
            activity.write_text(
                "package com.example\nimport io.flutter.embedding.android.FlutterActivity\nclass MainActivity : FlutterActivity()\n"
            )
            template = Path(__file__).resolve().parents[1] / "native" / "AppSpeechPlugin.kt"
            configure_speech(root, template)
            configure_speech(root, template)
            self.assertEqual(activity.read_text().count("plugins.add(AppSpeechPlugin())"), 1)
            plugin = (activity.parent / "AppSpeechPlugin.kt").read_text()
            self.assertTrue(plugin.startswith("package com.example\n"))
            self.assertNotIn("__APP_PACKAGE__", plugin)

    def test_does_not_overwrite_custom_activity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = root / "MainActivity.kt"
            original = (
                "package com.example\nclass MainActivity : FlutterActivity() { fun custom() {} }\n"
            )
            activity.write_text(original)
            with self.assertRaises(RuntimeError):
                configure_speech(root, Path("unused"))
            self.assertEqual(activity.read_text(), original)
