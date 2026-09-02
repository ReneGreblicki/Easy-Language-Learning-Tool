from __future__ import annotations

import random

import pytest

from easy_language_learning_tool.flashcards.models import FlashcardMode, FlashcardSession
from easy_language_learning_tool.workbook.service import RankedWorkbookRow


def rows(start: int, end: int) -> dict[int, RankedWorkbookRow]:
    return {
        rank: RankedWorkbookRow(
            rank=rank,
            foreign_word=f"word {rank}",
            word_translation=f"translation {rank}",
            foreign_sentence=f"Sentence {rank}.",
            sentence_translation=f"Translated sentence {rank}.",
        )
        for rank in range(start, end + 1)
    }


def test_navigation_visits_every_selected_rank_once() -> None:
    order = list(range(10, 1_010))
    random.Random(7).shuffle(order)
    session = FlashcardSession(
        source_id=1,
        source_path="example.xlsx",
        source_name="example.xlsx",
        source_row_count=1_200,
        mode=FlashcardMode.BOTH,
        from_rank=10,
        to_rank=1_009,
        order=order,
        rows=rows(10, 1_009),
    )
    visited = [session.current_rank]
    while session.next():
        visited.append(session.current_rank)
    assert len(visited) == 1_000
    assert len(set(visited)) == 1_000
    assert sorted(visited) == list(range(10, 1_010))
    assert not session.can_next
    assert session.previous()
    assert session.position == 998


def test_shuffle_again_avoids_immediate_boundary_repeat() -> None:
    session = FlashcardSession(
        source_id=1,
        source_path="example.xlsx",
        source_name="example.xlsx",
        source_row_count=3,
        mode=FlashcardMode.WORDS,
        from_rank=1,
        to_rank=3,
        order=[1, 2, 3],
        rows=rows(1, 3),
        position=2,
        showing_back=True,
    )
    previous = session.current_rank
    session.shuffle_again(random.Random(2))
    assert session.current_rank != previous
    assert sorted(session.order) == [1, 2, 3]
    assert session.position == 0
    assert not session.showing_back


def test_session_rejects_duplicate_or_missing_ranks() -> None:
    with pytest.raises(ValueError, match="every eligible rank exactly once"):
        FlashcardSession(
            source_id=1,
            source_path="example.xlsx",
            source_name="example.xlsx",
            source_row_count=3,
            mode=FlashcardMode.SENTENCES,
            from_rank=1,
            to_rank=3,
            order=[1, 1, 3],
            rows=rows(1, 3),
        )
