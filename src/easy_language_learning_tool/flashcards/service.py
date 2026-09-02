from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from easy_language_learning_tool.persistence.database import database_connection
from easy_language_learning_tool.workbook.service import RankedWorkbookRow, import_ranked_xlsx

from .models import FlashcardMode, FlashcardSession


class FlashcardService:
    """Import ranked workbook rows and persist one resumable study session."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def import_workbook(self, path: Path) -> tuple[int, int]:
        resolved = path.expanduser().resolve()
        rows = import_ranked_xlsx(resolved)
        checksum = self._checksum(resolved)
        with database_connection(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            existing = connection.execute(
                "SELECT id FROM flashcard_sources WHERE file_checksum = ?", (checksum,)
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO flashcard_sources(
                        file_checksum, source_path, display_name, row_count
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (checksum, str(resolved), resolved.name, len(rows)),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("The flashcard workbook could not be indexed.")
                source_id = cursor.lastrowid
                connection.executemany(
                    """
                    INSERT INTO flashcard_rows(
                        source_id, rank, foreign_word, word_translation,
                        foreign_sentence, sentence_translation
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            source_id,
                            row.rank,
                            row.foreign_word,
                            row.word_translation,
                            row.foreign_sentence,
                            row.sentence_translation,
                        )
                        for row in rows
                    ],
                )
            else:
                source_id = int(existing[0])
                connection.execute(
                    """
                    UPDATE flashcard_sources
                    SET source_path = ?, display_name = ?, imported_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (str(resolved), resolved.name, source_id),
                )
        return source_id, len(rows)

    def start_session(
        self,
        source_id: int,
        mode: FlashcardMode,
        from_rank: int,
        to_rank: int,
        *,
        rng: random.Random | random.SystemRandom | None = None,
    ) -> FlashcardSession:
        rows = self._load_rows(source_id, from_rank, to_rank)
        if not rows:
            raise ValueError("The selected rank range does not contain any cards.")
        expected = list(range(from_rank, to_rank + 1))
        if sorted(rows) != expected:
            raise ValueError("The selected workbook ranks are not continuous.")
        order = expected.copy()
        (rng or random.SystemRandom()).shuffle(order)
        source_path, source_name, source_row_count = self._source_details(source_id)
        session = FlashcardSession(
            source_id=source_id,
            source_path=source_path,
            source_name=source_name,
            source_row_count=source_row_count,
            mode=mode,
            from_rank=from_rank,
            to_rank=to_rank,
            order=order,
            rows=rows,
        )
        self.save(session)
        return session

    def resume(self) -> FlashcardSession | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT s.source_id, f.source_path, f.display_name, f.row_count, s.mode,
                       s.from_rank, s.to_rank, s.order_json, s.position, s.showing_back
                FROM flashcard_sessions s
                JOIN flashcard_sources f ON f.id = s.source_id
                WHERE s.id = 1
                """
            ).fetchone()
        if row is None:
            return None
        source_id, source_path, source_name = int(row[0]), str(row[1]), str(row[2])
        from_rank, to_rank = int(row[5]), int(row[6])
        order = [int(value) for value in json.loads(str(row[7]))]
        rows = self._load_rows(source_id, from_rank, to_rank)
        return FlashcardSession(
            source_id=source_id,
            source_path=source_path,
            source_name=source_name,
            source_row_count=int(row[3]),
            mode=FlashcardMode(str(row[4])),
            from_rank=from_rank,
            to_rank=to_rank,
            order=order,
            rows=rows,
            position=int(row[8]),
            showing_back=bool(row[9]),
        )

    def save(self, session: FlashcardSession) -> None:
        with database_connection(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO flashcard_sessions(
                    id, source_id, mode, from_rank, to_rank, order_json,
                    position, showing_back, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    source_id = excluded.source_id,
                    mode = excluded.mode,
                    from_rank = excluded.from_rank,
                    to_rank = excluded.to_rank,
                    order_json = excluded.order_json,
                    position = excluded.position,
                    showing_back = excluded.showing_back,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    session.source_id,
                    session.mode.value,
                    session.from_rank,
                    session.to_rank,
                    json.dumps(session.order, separators=(",", ":")),
                    session.position,
                    int(session.showing_back),
                ),
            )

    def _source_details(self, source_id: int) -> tuple[str, str, int]:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT source_path, display_name, row_count FROM flashcard_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            raise ValueError("The selected flashcard workbook is no longer available.")
        return str(row[0]), str(row[1]), int(row[2])

    def _load_rows(
        self, source_id: int, from_rank: int, to_rank: int
    ) -> dict[int, RankedWorkbookRow]:
        with database_connection(self.database_path) as connection:
            records = connection.execute(
                """
                SELECT rank, foreign_word, word_translation,
                       foreign_sentence, sentence_translation
                FROM flashcard_rows
                WHERE source_id = ? AND rank BETWEEN ? AND ?
                ORDER BY rank
                """,
                (source_id, from_rank, to_rank),
            ).fetchall()
        return {
            int(record[0]): RankedWorkbookRow(
                rank=int(record[0]),
                foreign_word=str(record[1]),
                word_translation=str(record[2]),
                foreign_sentence=str(record[3]),
                sentence_translation=str(record[4]),
            )
            for record in records
        }
