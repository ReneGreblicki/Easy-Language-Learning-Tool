from __future__ import annotations

import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

if sys.platform != "win32":
    pytest.skip("Windows desktop smoke test", allow_module_level=True)

from easy_language_learning_tool.config.paths import AppPaths  # noqa: E402
from easy_language_learning_tool.domain.enums import Language  # noqa: E402
from easy_language_learning_tool.persistence.database import initialize_database  # noqa: E402
from easy_language_learning_tool.ui.main_window import MainWindow  # noqa: E402
from easy_language_learning_tool.workbook.service import SENTENCE_HEADERS  # noqa: E402


def make_workbook(path: Path, count: int = 4) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sentences"
    sheet.append(SENTENCE_HEADERS)
    for rank in range(1, count + 1):
        sheet.append(
            (
                f"palabra {rank}",
                f"word {rank}",
                f"La frase número {rank}.",
                f"Sentence number {rank}.",
            )
        )
    workbook.save(path)


def test_main_window_tabs_and_generation_limits(qtbot: object, tmp_path: Path) -> None:
    paths = AppPaths(tmp_path / "data", tmp_path / "cache", tmp_path / "logs", tmp_path / "history")
    paths.create()
    initialize_database(paths.data / "easy_language_learning_tool.sqlite3")
    window = MainWindow(paths)
    qtbot.addWidget(window)  # type: ignore[attr-defined]
    window.size_and_center()
    assert window.tabs.count() == 4
    assert [window.tabs.tabText(index) for index in range(4)] == [
        "Sentence Creation",
        "Flashcards",
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


def test_flashcard_combined_mode_range_navigation_and_resume(qtbot: object, tmp_path: Path) -> None:
    paths = AppPaths(tmp_path / "data", tmp_path / "cache", tmp_path / "logs", tmp_path / "history")
    paths.create()
    initialize_database(paths.data / "easy_language_learning_tool.sqlite3")
    workbook = tmp_path / "cards.xlsx"
    make_workbook(workbook)
    window = MainWindow(paths)
    qtbot.addWidget(window)  # type: ignore[attr-defined]
    window._load_flashcard_workbook(workbook)

    session = window._flashcard_session
    assert session is not None
    assert len(session.order) == 4
    assert len(set(session.order)) == 4
    rank = session.current_rank
    assert window.flashcard_word.text() == f"palabra {rank}"
    assert window.flashcard_sentence.text() == f"La frase número {rank}."
    assert window.flashcard_word.font().bold()
    assert window.flashcard_word.font().pointSize() > window.flashcard_sentence.font().pointSize()

    window.flip_flashcard()
    assert window.flashcard_word.text() == f"word {rank}"
    assert window.flashcard_sentence.text() == f"Sentence number {rank}."
    window.flashcard_selected_rows.setChecked(True)
    window.flashcard_from_rank.setText("2")
    window.flashcard_to_rank.setText("3")
    window._apply_flashcard_range()
    assert window._flashcard_session is not None
    assert sorted(window._flashcard_session.order) == [2, 3]

    restored_window = MainWindow(paths)
    qtbot.addWidget(restored_window)  # type: ignore[attr-defined]
    restored = restored_window._flashcard_session
    assert restored is not None
    assert restored.order == window._flashcard_session.order
    assert restored.from_rank == 2
    assert restored.to_rank == 3
