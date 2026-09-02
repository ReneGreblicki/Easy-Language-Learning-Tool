from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from easy_language_learning_tool.ui.controls import (
    DeliberateWheelComboBox,
    DeliberateWheelSlider,
    DeliberateWheelSpinBox,
)


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


def test_combo_always_ignores_wheel_even_after_click(qtbot: object) -> None:
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
    after_click = wheel_event(-120)
    QApplication.sendEvent(combo, after_click)
    assert combo.currentIndex() == 1
    assert not after_click.isAccepted()

    combo.clearFocus()
    disarmed = wheel_event(120)
    QApplication.sendEvent(combo, disarmed)
    assert combo.currentIndex() == 1
    assert not disarmed.isAccepted()


def test_spin_box_always_ignores_wheel_even_after_click(qtbot: object) -> None:
    spin = DeliberateWheelSpinBox()
    spin.setRange(0, 10)
    spin.setValue(5)
    qtbot.addWidget(spin)  # type: ignore[attr-defined]
    spin.show()

    hovered = wheel_event(120)
    QApplication.sendEvent(spin, hovered)
    assert spin.value() == 5
    assert not hovered.isAccepted()

    qtbot.mouseClick(spin, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    value_after_click = spin.value()
    clicked = wheel_event(120)
    QApplication.sendEvent(spin, clicked)
    assert spin.value() == value_after_click
    assert not clicked.isAccepted()

    clicked_value = spin.value()
    spin.clearFocus()
    after_focus_left = wheel_event(120)
    QApplication.sendEvent(spin, after_focus_left)
    assert spin.value() == clicked_value
    assert not after_focus_left.isAccepted()


def test_slider_always_ignores_wheel_even_after_click(qtbot: object) -> None:
    slider = DeliberateWheelSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 10)
    slider.setValue(5)
    qtbot.addWidget(slider)  # type: ignore[attr-defined]
    slider.show()

    hovered = wheel_event(120)
    QApplication.sendEvent(slider, hovered)
    assert slider.value() == 5
    assert not hovered.isAccepted()

    qtbot.mouseClick(slider, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    value_after_click = slider.value()
    clicked = wheel_event(120)
    QApplication.sendEvent(slider, clicked)
    assert slider.value() == value_after_click
    assert not clicked.isAccepted()

    clicked_value = slider.value()
    slider.clearFocus()
    after_focus_left = wheel_event(120)
    QApplication.sendEvent(slider, after_focus_left)
    assert slider.value() == clicked_value
    assert not after_focus_left.isAccepted()
