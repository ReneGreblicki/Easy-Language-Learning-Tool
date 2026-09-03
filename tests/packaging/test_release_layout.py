from __future__ import annotations

from pathlib import Path


def test_release_support_files_are_present() -> None:
    root = Path(__file__).resolve().parents[2]
    required = (
        root / "README.md",
        root / "RELEASE_NOTES.md",
        root / "uv.lock",
        root / "assets" / "icons" / "logo.png",
        root / "assets" / "icons" / "logo.ico",
        root / "examples" / "Expected_Workbook_Format.xlsx",
        root / "installer" / "inno_setup.iss",
        root / "installer" / "sign_windows_artifacts.ps1",
        root / "installer" / "windows_acceptance.ps1",
        root / "resources" / "licences" / "FFMPEG_NOTICE.md",
        root / "resources" / "licences" / "WORDFREQ_NOTICE.md",
        root / "resources" / "licences" / "WIKTIONARY_NOTICE.md",
        root / "resources" / "licences" / "THAI_DATA_NOTICE.md",
        root / "resources" / "USER_MANUAL.md",
        root / "resources" / "frequency_data" / "README.md",
        root / "resources" / "frequency_data" / "THAI_SOURCE_MANIFEST.json",
        root / "resources" / "frequency_data" / "production" / "words.jsonl.gz",
    )
    assert all(path.is_file() for path in required)

    manual = (root / "resources" / "USER_MANUAL.md").read_text(encoding="utf-8")
    assert manual.startswith("# 1. Sentence Creation")
    assert "# 6. Common problems" in manual
    assert "# 3. Sentence Creation" not in manual


def test_windows_workflow_runs_installer_acceptance_and_supports_signing() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
    assert "installer\\windows_acceptance.ps1" in workflow
    assert "installer\\sign_windows_artifacts.ps1" in workflow
    assert "Copy-Item installer\\bundled\\ffmpeg\\ffmpeg.exe" in workflow
    assert "Copy-Item installer\\bundled\\ffmpeg\\ffprobe.exe" in workflow
    assert "actions/upload-artifact@v6" in workflow
    assert "Select-String -Path pyproject.toml" in workflow
    assert "github.event.pull_request.head.sha" in workflow
    assert "--windows-icon-from-ico=assets/icons/logo.ico" in workflow
    assert "ExtractAssociatedIcon" in workflow
    assert '"version=0.4.0"' not in workflow

    installer = (root / "installer" / "inno_setup.iss").read_text(encoding="utf-8")
    assert "SetupIconFile=..\\assets\\icons\\logo.ico" in installer
    assert "UninstallDisplayIcon={app}\\{#MyAppExeName}" in installer
