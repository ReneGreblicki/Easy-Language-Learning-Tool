from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from easy_language_learning_tool.persistence.database import database_connection
from easy_language_learning_tool.sync.models import SyncOperation


class SyncOutbox:
    """Persist idempotent sync work before any network request is attempted."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def enqueue(self, operation: SyncOperation) -> None:
        with database_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO sync_outbox(
                    id, entity_type, entity_id, operation, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    str(operation.id),
                    operation.entity_type,
                    str(operation.entity_id),
                    operation.operation.value,
                    operation.model_dump_json(),
                    operation.created_at.isoformat(),
                ),
            )

    def pending(self, limit: int = 100) -> list[SyncOperation]:
        if limit < 1:
            raise ValueError("The outbox limit must be positive.")
        now = datetime.now(UTC).isoformat()
        with database_connection(self.database_path) as connection:
            rows: Sequence[sqlite3.Row] = connection.execute(
                """
                SELECT payload_json
                FROM sync_outbox
                WHERE available_at <= ?
                ORDER BY created_at
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        return [SyncOperation.model_validate_json(row[0]) for row in rows]

    def acknowledge(self, operation_id: str) -> None:
        with database_connection(self.database_path) as connection:
            connection.execute("DELETE FROM sync_outbox WHERE id = ?", (operation_id,))

    def record_failure(self, operation_id: str, error: str) -> None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT attempts FROM sync_outbox WHERE id = ?", (operation_id,)
            ).fetchone()
            if row is None:
                return
            attempts = int(row[0]) + 1
            delay = min(2**attempts, 3600)
            available_at = datetime.now(UTC) + timedelta(seconds=delay)
            connection.execute(
                """
                UPDATE sync_outbox
                SET attempts = ?, available_at = ?, last_error = ?
                WHERE id = ?
                """,
                (attempts, available_at.isoformat(), error[:1000], operation_id),
            )
