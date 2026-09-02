from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QComboBox, QFrame, QSlider, QSpinBox, QWidget


class ScrollPage(QWidget):
    """A scroll-page body that takes focus when its empty background is clicked."""

    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)


class ClickableFrame(QFrame):
    clicked = Signal()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class DeliberateWheelComboBox(QComboBox):
    """Never let page-scrolling change a closed dropdown selection."""

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        event.ignore()


class DeliberateWheelSpinBox(QSpinBox):
    """Never let page-scrolling change a numeric selection."""

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        event.ignore()


class DeliberateWheelSlider(QSlider):
    """Never let page-scrolling change a slider value."""

    def __init__(self, orientation: Qt.Orientation) -> None:
        super().__init__(orientation)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        event.ignore()
