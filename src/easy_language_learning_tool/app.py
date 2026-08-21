from __future__ import annotations

import sys

from easy_language_learning_tool.config.logging import configure_logging
from easy_language_learning_tool.config.paths import resolve_app_paths
from easy_language_learning_tool.persistence.database import initialize_database


def main() -> int:
    try:
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
    application = QApplication(sys.argv)
    application.setApplicationName("Easy Language Learning Tool")
    window = MainWindow()
    window.size_and_center()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
