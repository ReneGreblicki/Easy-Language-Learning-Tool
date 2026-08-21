from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class TaskThread(QThread):
    """Run one blocking or async callable without freezing the Qt event loop."""

    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            result = self._task()
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            self.succeeded.emit(result)
        except Exception as error:
            self.failed.emit(str(error))
