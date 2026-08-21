from __future__ import annotations

import unittest
from decimal import Decimal

from pydantic import ValidationError

from easy_language_learning_tool.domain.enums import (
    CEFR_MAX_WORDS,
    CefrLevel,
    CefrMode,
    Language,
    SentenceKind,
)
from easy_language_learning_tool.domain.models import CefrSelection, GenerationSettings, VerbRecord
from easy_language_learning_tool.domain.planner import build_generation_plan
from easy_language_learning_tool.domain.rules import (
    grammatical_person_schedule,
    largest_remainder_allocation,
)


def single_level(level: CefrLevel = CefrLevel.A1) -> CefrSelection:
    return CefrSelection(mode=CefrMode.SINGLE, single_level=level)


def settings(**overrides: object) -> GenerationSettings:
    values: dict[str, object] = {
        "learning_language": Language.GERMAN,
        "translation_language": Language.US_ENGLISH,
        "base_sentences": 10,
        "extra_forms": 0,
        "question_percentage": Decimal("20"),
        "pronoun_change": 3,
        "cefr": single_level(),
        "seed": 42,
    }
    values.update(overrides)
    return GenerationSettings(**values)


class ProductRuleTests(unittest.TestCase):
    def test_cefr_word_limits_are_locked(self) -> None:
        self.assertEqual(list(CEFR_MAX_WORDS.values()), [5, 8, 11, 14, 17, 20])

    def test_largest_remainder_reconciles_and_ties_follow_level_order(self) -> None:
        result = largest_remainder_allocation(
            7,
            {CefrLevel.A1: Decimal("50"), CefrLevel.A2: Decimal("50")},
            (CefrLevel.A1, CefrLevel.A2),
        )
        self.assertEqual(result, {CefrLevel.A1: 4, CefrLevel.A2: 3})
        self.assertEqual(sum(result.values()), 7)

    def test_gradual_mode_requires_exactly_100_percent(self) -> None:
        with self.assertRaises(ValidationError):
            CefrSelection(
                mode=CefrMode.GRADUAL,
                start_level=CefrLevel.A1,
                end_level=CefrLevel.B1,
                percentages={
                    CefrLevel.A1: Decimal("30"),
                    CefrLevel.A2: Decimal("40"),
                    CefrLevel.B1: Decimal("29"),
                },
            )

    def test_extra_forms_limit_matrix(self) -> None:
        self.assertEqual(settings(base_sentences=1_000, extra_forms=4).final_rows, 5_000)
        with self.assertRaises(ValidationError):
            settings(base_sentences=1_001, extra_forms=1)
        with self.assertRaises(ValidationError):
            settings(base_sentences=1_000, extra_forms=5)

    def test_languages_must_differ(self) -> None:
        with self.assertRaises(ValidationError):
            settings(translation_language=Language.GERMAN)

    def test_pronoun_schedule_is_deterministic_and_changes_on_boundary(self) -> None:
        first = grammatical_person_schedule(25, 2, 77)
        second = grammatical_person_schedule(25, 2, 77)
        self.assertEqual(first, second)
        self.assertEqual(len(set(first[:20])), 1)
        self.assertNotEqual(first[19], first[20])

    def test_plan_expands_forms_and_keeps_base_attributes(self) -> None:
        config = settings(base_sentences=5, extra_forms=2, question_percentage=Decimal("40"))
        verbs = [VerbRecord(rank=index, lemma=f"verb-{index}") for index in range(1, 6)]
        plan = build_generation_plan(config, verbs)
        self.assertEqual(len(plan), 15)
        self.assertEqual(sum(row.form_index == 0 for row in plan), 5)
        self.assertEqual(
            sum(row.form_index == 0 and row.sentence_kind is SentenceKind.QUESTION for row in plan),
            2,
        )
        for offset in range(0, 15, 3):
            group = plan[offset : offset + 3]
            self.assertEqual(len({row.verb.lemma for row in group}), 1)
            self.assertEqual(len({row.cefr_level for row in group}), 1)
            self.assertEqual([row.form_index for row in group], [0, 1, 2])

    def test_duplicate_base_lemmas_are_rejected(self) -> None:
        config = settings(base_sentences=2)
        verbs = [VerbRecord(rank=1, lemma="gehen"), VerbRecord(rank=2, lemma="Gehen")]
        with self.assertRaises(ValueError):
            build_generation_plan(config, verbs)


if __name__ == "__main__":
    unittest.main()
