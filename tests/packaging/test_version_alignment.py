from __future__ import annotations

import re
import tomllib
from pathlib import Path

from easy_language_learning_tool import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_is_aligned_across_project_files() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project_version = tomllib.load(handle)["project"]["version"]

    installer = (ROOT / "installer" / "inno_setup.iss").read_text(encoding="utf-8")
    installer_match = re.search(r'^#define MyAppVersion "([^"]+)"$', installer, re.MULTILINE)

    assert project_version == "1.3.0"
    assert __version__ == project_version
    assert installer_match is not None
    assert installer_match.group(1) == project_version
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "releases/download/v1.1.0/EasyLanguageLearningTool-Setup-1.1.0.exe" in readme
    assert f"Tool {project_version}" in (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
