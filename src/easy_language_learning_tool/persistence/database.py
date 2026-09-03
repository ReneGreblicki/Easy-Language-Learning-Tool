from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2


@contextmanager
def database_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Return a transactional connection that is always closed explicitly."""
    connection = sqlite3.connect(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(path: Path) -> None:
    """Create the Phase-0 database atomically using only local app data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with database_connection(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS history_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_type TEXT NOT NULL CHECK(file_type IN ('workbook', 'audio')),
                owned_path TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                settings_json TEXT,
                status TEXT NOT NULL DEFAULT 'complete'
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                state TEXT NOT NULL,
                settings_checksum TEXT NOT NULL,
                input_checksum TEXT,
                last_completed_row INTEGER NOT NULL DEFAULT 0,
                manifest_path TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS flashcard_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_checksum TEXT NOT NULL UNIQUE,
                source_path TEXT NOT NULL,
                display_name TEXT NOT NULL,
                row_count INTEGER NOT NULL CHECK(row_count BETWEEN 1 AND 5000),
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS flashcard_rows (
                source_id INTEGER NOT NULL REFERENCES flashcard_sources(id) ON DELETE CASCADE,
                rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 5000),
                foreign_word TEXT NOT NULL,
                word_translation TEXT NOT NULL,
                foreign_sentence TEXT NOT NULL,
                sentence_translation TEXT NOT NULL,
                PRIMARY KEY(source_id, rank)
            );
            CREATE TABLE IF NOT EXISTS flashcard_sessions (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                source_id INTEGER NOT NULL REFERENCES flashcard_sources(id) ON DELETE CASCADE,
                mode TEXT NOT NULL CHECK(mode IN ('words', 'sentences', 'both')),
                from_rank INTEGER NOT NULL CHECK(from_rank BETWEEN 1 AND 5000),
                to_rank INTEGER NOT NULL CHECK(to_rank BETWEEN 1 AND 5000),
                order_json TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                showing_back INTEGER NOT NULL DEFAULT 0 CHECK(showing_back IN (0, 1)),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK(from_rank <= to_rank)
            );
            """
        )
        row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        elif row[0] == 1:
            connection.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        elif row[0] != SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported database schema version: {row[0]}")
