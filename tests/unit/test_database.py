from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from easy_language_learning_tool.persistence.database import (
    SCHEMA_VERSION,
    database_connection,
    initialize_database,
)


class DatabaseTests(unittest.TestCase):
    def test_database_bootstrap_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.sqlite3"
            initialize_database(path)
            initialize_database(path)
            with database_connection(path) as connection:
                version = connection.execute("SELECT version FROM schema_version").fetchone()
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertEqual(version, (SCHEMA_VERSION,))
            self.assertTrue(
                {
                    "app_settings",
                    "history_items",
                    "jobs",
                    "flashcard_sources",
                    "flashcard_rows",
                    "flashcard_sessions",
                }.issubset(tables)
            )

    def test_version_one_database_migrates_without_losing_existing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.sqlite3"
            with database_connection(path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE schema_version (version INTEGER NOT NULL);
                    INSERT INTO schema_version(version) VALUES (1);
                    CREATE TABLE app_settings (
                        key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    INSERT INTO app_settings(key, value_json) VALUES ('theme', '"dark"');
                    """
                )
            initialize_database(path)
            with database_connection(path) as connection:
                version = connection.execute("SELECT version FROM schema_version").fetchone()
                setting = connection.execute(
                    "SELECT value_json FROM app_settings WHERE key = 'theme'"
                ).fetchone()
            self.assertEqual(version, (SCHEMA_VERSION,))
            self.assertEqual(setting, ('"dark"',))


if __name__ == "__main__":
    unittest.main()
