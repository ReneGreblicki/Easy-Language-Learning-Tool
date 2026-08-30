from __future__ import annotations

import sys
from pathlib import Path

import pytest

if sys.platform != "win32":
    pytest.skip("Windows desktop smoke test", allow_module_level=True)

from easy_language_learning_tool.config.paths import AppPaths  # noqa: E402
from easy_language_learning_tool.domain.enums import Language  # noqa: E402
from easy_language_learning_tool.persistence.database import initialize_database  # noqa: E402
from easy_language_learning_tool.ui.main_window import MainWindow  # noqa: E402


def test_main_window_tabs_and_generation_limits(qtbot: object, tmp_path: Path) -> None:
    paths = AppPaths(tmp_path / "data", tmp_path / "cache", tmp_path / "logs", tmp_path / "history")
    paths.create()
    initialize_database(paths.data / "easy_language_learning_tool.sqlite3")
    window = MainWindow(paths)
    qtbot.addWidget(window)  # type: ignore[attr-defined]
    window.size_and_center()
    assert window.tabs.count() == 3
    assert [window.tabs.tabText(index) for index in range(3)] == [
        "Sentence Creation",
        "TTS",
        "History",
    ]
    assert window.base_count.maximum() == 5_000
    assert window.learning.currentData() == Language.EUROPEAN_SPANISH
    assert window.translation.currentData() == Language.US_ENGLISH
    assert window.foreign_language.currentData() == Language.EUROPEAN_SPANISH
    assert window.translation_language.currentData() == Language.US_ENGLISH
    assert window.frequency_status.text() == (
        "Production dataset: 5,000 ranked European Spanish words. Examples will be AI generated "
        "in European Spanish and translated into US English. Missing word translations will also "
        "be AI generated in US English."
    )
    extra_row, _ = window.sentence_settings_form.getWidgetPosition(window.extra_forms)
    output_row, _ = window.sentence_settings_form.getWidgetPosition(window.final_rows)
    assert output_row == extra_row + 1
    assert window.pronouns.currentText() == "0"
    assert "Every sentence uses a neutral or impersonal" in window.pronoun_explanation.text()
    window.pronouns.setCurrentText("3")
    assert "60% use a randomly selected" in window.pronoun_explanation.text()
    window.learning.setCurrentIndex(window.learning.findData(Language.US_ENGLISH))
    window.translation.setCurrentIndex(window.translation.findData(Language.EUROPEAN_SPANISH))
    assert window.frequency_status.text() == (
        "Production dataset: 5,000 ranked US English words. Examples will be AI generated in US "
        "English and translated into European Spanish. Missing word translations will also be "
        "AI generated in European Spanish."
    )
    window.frequency_repository.available_count = lambda *_: 5_000  # type: ignore[method-assign]
    window.refresh_sentence_state()
    window.extra_forms.setCurrentText("1")
    assert window.extra_forms.isEnabled()
    assert window.base_count.maximum() == 2_500
    window.base_count.setValue(2_500)
    assert "5,000 final rows" in window.final_rows.text()
    assert "5,000 rows" in window.findChild(type(window.frequency_status), "rowLimitNotice").text()
