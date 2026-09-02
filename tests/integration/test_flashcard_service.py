from __future__ import annotations

import random
from pathlib import Path

from openpyxl import Workbook

from easy_language_learning_tool.flashcards import FlashcardMode, FlashcardService
from easy_language_learning_tool.persistence.database import initialize_database
from easy_language_learning_tool.workbook.service import SENTENCE_HEADERS


def make_workbook(path: Path, count: int = 10) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sentences"
    sheet.append(SENTENCE_HEADERS)
    for rank in range(1, count + 1):
        sheet.append(
            (
                f"foreign word {rank}",
                f"word translation {rank}",
                f"Foreign sentence {rank}.",
                f"Sentence translation {rank}.",
            )
        )
    workbook.save(path)


def test_ranked_import_and_session_resume(tmp_path: Path) -> None:
    database = tmp_path / "app.sqlite3"
    initialize_database(database)
    workbook = tmp_path / "cards.xlsx"
    make_workbook(workbook)
    service = FlashcardService(database)
    source_id, count = service.import_workbook(workbook)
    repeated_source_id, repeated_count = service.import_workbook(workbook)
    assert (count, repeated_count) == (10, 10)
    assert repeated_source_id == source_id

    session = service.start_session(source_id, FlashcardMode.BOTH, 2, 8, rng=random.Random(7))
    assert sorted(session.order) == list(range(2, 9))
    assert session.current_row.rank == session.current_rank
    session.next()
    session.flip()
    service.save(session)

    restored = service.resume()
    assert restored is not None
    assert restored.source_id == source_id
    assert restored.source_row_count == 10
    assert restored.mode is FlashcardMode.BOTH
    assert restored.from_rank == 2
    assert restored.to_rank == 8
    assert restored.order == session.order
    assert restored.position == session.position
    assert restored.showing_back
    assert restored.current_row == session.current_row
