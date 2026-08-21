from __future__ import annotations

from pathlib import Path


def test_release_support_files_are_present() -> None:
    root = Path(__file__).resolve().parents[2]
    required = (
        root / "README.md",
        root / "RELEASE_NOTES.md",
        root / "uv.lock",
        root / "assets" / "icons" / "logo.svg",
        root / "examples" / "Expected_Workbook_Format.xlsx",
        root / "installer" / "inno_setup.iss",
        root / "resources" / "licences" / "FFMPEG_NOTICE.md",
        root / "resources" / "licences" / "WORDFREQ_NOTICE.md",
        root / "resources" / "licences" / "WIKTIONARY_NOTICE.md",
        root / "resources" / "frequency_data" / "README.md",
    )
    assert all(path.is_file() for path in required)
