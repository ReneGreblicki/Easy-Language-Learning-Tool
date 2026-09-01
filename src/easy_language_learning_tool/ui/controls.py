from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFocusEvent, QMouseEvent, QWheelEvent
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
    """Ignore wheel changes until this exact control is clicked."""

    def __init__(self) -> None:
        super().__init__()
        self._wheel_armed = False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = True
        super().mousePressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = event.reason() == Qt.FocusReason.MouseFocusReason
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = False
        super().focusOutEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        if self._wheel_armed and self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class DeliberateWheelSpinBox(QSpinBox):
    """Ignore wheel changes until this exact control is clicked."""

    def __init__(self) -> None:
        super().__init__()
        self._wheel_armed = False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = True
        super().mousePressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = event.reason() == Qt.FocusReason.MouseFocusReason
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = False
        super().focusOutEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        if self._wheel_armed and self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class DeliberateWheelSlider(QSlider):
    """Ignore wheel changes until this exact control is clicked."""

    def __init__(self, orientation: Qt.Orientation) -> None:
        super().__init__(orientation)
        self._wheel_armed = False

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = True
        super().mousePressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = event.reason() == Qt.FocusReason.MouseFocusReason
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802 - Qt API
        self._wheel_armed = False
        super().focusOutEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt API
        if self._wheel_armed and self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
