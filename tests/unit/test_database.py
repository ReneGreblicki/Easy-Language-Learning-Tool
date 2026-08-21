from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from easy_language_learning_tool.persistence.database import SCHEMA_VERSION, initialize_database


class DatabaseTests(unittest.TestCase):
    def test_database_bootstrap_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.sqlite3"
            initialize_database(path)
            initialize_database(path)
            with sqlite3.connect(path) as connection:
                version = connection.execute("SELECT version FROM schema_version").fetchone()
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertEqual(version, (SCHEMA_VERSION,))
            self.assertTrue({"app_settings", "history_items", "jobs"}.issubset(tables))


if __name__ == "__main__":
    unittest.main()
