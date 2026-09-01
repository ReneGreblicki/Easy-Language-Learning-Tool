from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum

from easy_language_learning_tool.workbook.service import RankedWorkbookRow


class FlashcardMode(StrEnum):
    WORDS = "words"
    SENTENCES = "sentences"
    BOTH = "both"

    @property
    def label(self) -> str:
        return {
            FlashcardMode.WORDS: "Words",
            FlashcardMode.SENTENCES: "Sentences",
            FlashcardMode.BOTH: "Words and sentences",
        }[self]


@dataclass
class FlashcardSession:
    source_id: int
    source_path: str
    source_name: str
    source_row_count: int
    mode: FlashcardMode
    from_rank: int
    to_rank: int
    order: list[int]
    rows: dict[int, RankedWorkbookRow]
    position: int = 0
    showing_back: bool = False

    def __post_init__(self) -> None:
        if not self.order:
            raise ValueError("A flashcard session requires at least one eligible row.")
        if not 1 <= self.from_rank <= self.to_rank:
            raise ValueError("The flashcard rank range is invalid.")
        if self.to_rank > self.source_row_count:
            raise ValueError("The flashcard rank range exceeds the workbook row count.")
        if set(self.order) != set(range(self.from_rank, self.to_rank + 1)):
            raise ValueError("The flashcard order must contain every eligible rank exactly once.")
        if not 0 <= self.position < len(self.order):
            raise ValueError("The flashcard position is outside the shuffled order.")
        if set(self.order) != set(self.rows):
            raise ValueError("The stored flashcard rows do not match the shuffled order.")

    @property
    def current_rank(self) -> int:
        return self.order[self.position]

    @property
    def current_row(self) -> RankedWorkbookRow:
        return self.rows[self.current_rank]

    @property
    def can_previous(self) -> bool:
        return self.position > 0

    @property
    def can_next(self) -> bool:
        return self.position + 1 < len(self.order)

    def previous(self) -> bool:
        if not self.can_previous:
            return False
        self.position -= 1
        self.showing_back = False
        return True

    def next(self) -> bool:
        if not self.can_next:
            return False
        self.position += 1
        self.showing_back = False
        return True

    def flip(self) -> None:
        self.showing_back = not self.showing_back

    def shuffle_again(self, rng: random.Random | random.SystemRandom | None = None) -> None:
        generator = rng or random.SystemRandom()
        previous_rank = self.current_rank
        generator.shuffle(self.order)
        if len(self.order) > 1 and self.order[0] == previous_rank:
            self.order[0], self.order[1] = self.order[1], self.order[0]
        self.position = 0
        self.showing_back = False
