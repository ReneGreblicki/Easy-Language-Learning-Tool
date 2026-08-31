from __future__ import annotations

import sys
from pathlib import Path

from easy_language_learning_tool.config.logging import configure_logging
from easy_language_learning_tool.config.paths import resolve_app_paths
from easy_language_learning_tool.persistence.database import initialize_database


def _resource_path(*parts: str) -> Path:
    packaged = Path(sys.argv[0]).resolve().parent
    if packaged.joinpath(parts[0]).exists():
        return packaged.joinpath(*parts)
    return Path(__file__).resolve().parents[2].joinpath(*parts)


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "EasyLanguageLearningTool.Desktop.1"
    )


def main() -> int:
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError as error:
        raise SystemExit(
            'PySide6 is not installed. Run: python -m pip install -e ".[dev]"'
        ) from error

    from easy_language_learning_tool.ui.main_window import MainWindow

    paths = resolve_app_paths()
    paths.create()
    configure_logging(paths.logs / "application.log")
    initialize_database(paths.data / "easy_language_learning_tool.sqlite3")
    _set_windows_app_id()
    application = QApplication(sys.argv)
    application.setApplicationName("Easy Language Learning Tool")
    application.setApplicationDisplayName("Easy Language Learning Tool")
    application.setWindowIcon(QIcon(str(_resource_path("assets", "icons", "logo.ico"))))
    window = MainWindow()
    window.size_and_center()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
