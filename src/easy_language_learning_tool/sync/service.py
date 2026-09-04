from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from easy_language_learning_tool.persistence.database import database_connection
from easy_language_learning_tool.sync.client import CloudSession, SupabaseSyncClient
from easy_language_learning_tool.sync.models import (
    CardPayload,
    DeckPayload,
    SyncOperation,
    SyncOperationType,
)
from easy_language_learning_tool.sync.outbox import SyncOutbox

CARD_NAMESPACE = UUID("87399045-f531-4a2c-b1d0-f524a8733e60")


class DesktopSyncService:
    def __init__(self, database_path: Path, client: SupabaseSyncClient) -> None:
        self.database_path = database_path
        self.client = client
        self.outbox = SyncOutbox(database_path)

    def queue_source(
        self,
        source_id: int,
        *,
        source_language: str,
        translation_language: str,
        cefr_level: str | None = None,
        settings: dict[str, object] | None = None,
    ) -> UUID:
        with database_connection(self.database_path) as connection:
            source = connection.execute(
                """
                SELECT file_checksum, display_name
                FROM flashcard_sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()
            if source is None:
                raise ValueError(f"Unknown flashcard source: {source_id}")
            existing = connection.execute(
                "SELECT cloud_id, revision FROM sync_decks WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            deck_id = UUID(existing[0]) if existing else uuid5(CARD_NAMESPACE, source[0])
            revision = int(existing[1]) + 1 if existing else 1
            rows = connection.execute(
                """
                SELECT rank, foreign_word, word_translation,
                       foreign_sentence, sentence_translation
                FROM flashcard_rows
                WHERE source_id = ?
                ORDER BY rank
                """,
                (source_id,),
            ).fetchall()
            if not rows:
                raise ValueError("A deck must contain at least one card.")
            cards = [
                CardPayload(
                    id=uuid5(deck_id, str(row[0])),
                    rank=row[0],
                    foreign_word=row[1],
                    word_translation=row[2],
                    foreign_sentence=row[3],
                    sentence_translation=row[4],
                    revision=revision,
                )
                for row in rows
            ]
            deck = DeckPayload(
                id=deck_id,
                title=source[1],
                source_language=source_language,
                translation_language=translation_language,
                cefr_level=cefr_level,
                settings=settings or {},
                cards=cards,
                revision=revision,
            )
            operation = SyncOperation(
                id=uuid4(),
                entity_type="deck",
                entity_id=deck_id,
                operation=SyncOperationType.UPSERT,
                payload=json.loads(deck.model_dump_json()),
            )
            connection.execute(
                """
                INSERT INTO sync_decks(source_id, cloud_id, revision, sync_state)
                VALUES (?, ?, ?, 'pending')
                ON CONFLICT(source_id) DO UPDATE SET
                    revision = excluded.revision,
                    sync_state = 'pending'
                """,
                (source_id, str(deck_id), revision),
            )
        self.outbox.enqueue(operation)
        return deck_id

    def flush(self, session: CloudSession, limit: int = 100) -> tuple[int, int]:
        completed = 0
        failed = 0
        for operation in self.outbox.pending(limit):
            try:
                self.client.upload(operation, session)
            except Exception as error:
                self.outbox.record_failure(str(operation.id), str(error))
                failed += 1
                continue
            self.outbox.acknowledge(str(operation.id))
            with database_connection(self.database_path) as connection:
                connection.execute(
                    """
                    UPDATE sync_decks
                    SET sync_state = 'synced', last_synced_at = CURRENT_TIMESTAMP
                    WHERE cloud_id = ?
                    """,
                    (str(operation.entity_id),),
                )
            completed += 1
        return completed, failed
