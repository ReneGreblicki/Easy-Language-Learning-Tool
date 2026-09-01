from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from easy_language_learning_tool.ui.controls import DeliberateWheelComboBox


def wheel_event(delta: int) -> QWheelEvent:
    return QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )


def test_combo_ignores_wheel_until_explicitly_clicked(qtbot: object) -> None:
    combo = DeliberateWheelComboBox()
    combo.addItems(["One", "Two", "Three"])
    combo.setCurrentIndex(1)
    qtbot.addWidget(combo)  # type: ignore[attr-defined]
    combo.show()

    ignored = wheel_event(-120)
    QApplication.sendEvent(combo, ignored)
    assert combo.currentIndex() == 1
    assert not ignored.isAccepted()

    qtbot.mouseClick(combo, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    combo.hidePopup()
    accepted = wheel_event(-120)
    QApplication.sendEvent(combo, accepted)
    assert combo.currentIndex() == 2
