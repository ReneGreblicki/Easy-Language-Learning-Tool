from __future__ import annotations

import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess

from tool.configure_ios import (
    APP_LABEL,
    BUNDLE_ID,
    CALLBACK_SCHEME,
    MINIMUM_IOS_VERSION,
    configure_info_plist,
    configure_podfile,
    configure_xcode_project,
    install_icons,
)


class ConfigureIosTest(unittest.TestCase):
    def test_plist_gets_identity_callback_and_encryption_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plist_path = Path(directory) / "Info.plist"
            with plist_path.open("wb") as handle:
                plistlib.dump({"CFBundleURLTypes": []}, handle)
            configure_info_plist(plist_path)
            configure_info_plist(plist_path)
            with plist_path.open("rb") as handle:
                payload = plistlib.load(handle)
            self.assertEqual(payload["CFBundleDisplayName"], APP_LABEL)
            self.assertEqual(payload["CFBundleName"], APP_LABEL)
            self.assertFalse(payload["ITSAppUsesNonExemptEncryption"])
            callbacks = [
                scheme
                for item in payload["CFBundleURLTypes"]
                for scheme in item["CFBundleURLSchemes"]
                if scheme == CALLBACK_SCHEME
            ]
            self.assertEqual(callbacks, [CALLBACK_SCHEME])

    def test_xcode_project_gets_bundle_id_target_and_optional_team(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project.pbxproj"
            project.write_text(
                "IPHONEOS_DEPLOYMENT_TARGET = 12.0;\n"
                "PRODUCT_BUNDLE_IDENTIFIER = com.example.app;\n"
                "PRODUCT_BUNDLE_IDENTIFIER = com.example.app.RunnerTests;\n"
                "CODE_SIGN_STYLE = Automatic;\n",
                encoding="utf-8",
            )
            configure_xcode_project(project, team_id="ABCDE12345")
            text = project.read_text(encoding="utf-8")
            self.assertIn(f"IPHONEOS_DEPLOYMENT_TARGET = {MINIMUM_IOS_VERSION};", text)
            self.assertIn(f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};", text)
            self.assertIn(f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}.RunnerTests;", text)
            self.assertIn("DEVELOPMENT_TEAM = ABCDE12345;", text)

    def test_podfile_platform_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            podfile = Path(directory) / "Podfile"
            podfile.write_text("# platform :ios, '12.0'\nuse_frameworks!\n", encoding="utf-8")
            configure_podfile(podfile)
            configure_podfile(podfile)
            text = podfile.read_text(encoding="utf-8")
            self.assertEqual(text.count("platform :ios"), 1)
            self.assertIn(f"platform :ios, '{MINIMUM_IOS_VERSION}'", text)

    def test_icon_catalog_drives_every_required_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "logo.png"
            source.write_bytes(b"logo")
            catalog = root / "AppIcon.appiconset"
            catalog.mkdir()
            (catalog / "Contents.json").write_text(
                json.dumps(
                    {
                        "images": [
                            {"filename": "Icon-20@2x.png", "size": "20x20", "scale": "2x"},
                            {"filename": "Icon-1024.png", "size": "1024x1024", "scale": "1x"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def fake_runner(command: list[str], **_kwargs: object) -> CompletedProcess[str]:
                calls.append(command)
                return CompletedProcess(command, 0, "", "")

            install_icons(source, catalog, runner=fake_runner)
            self.assertEqual(calls[0][1:4], ["-z", "40", "40"])
            self.assertEqual(calls[1][1:4], ["-z", "1024", "1024"])


if __name__ == "__main__":
    unittest.main()
