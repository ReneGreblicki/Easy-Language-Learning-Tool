from __future__ import annotations

import unittest
from decimal import Decimal

from pydantic import ValidationError

from easy_language_learning_tool.domain.enums import (
    CEFR_MAX_WORDS,
    CefrLevel,
    CefrMode,
    GrammaticalPerson,
    Language,
    SentenceKind,
)
from easy_language_learning_tool.domain.models import CefrSelection, GenerationSettings, WordRecord
from easy_language_learning_tool.domain.planner import build_generation_plan
from easy_language_learning_tool.domain.rules import (
    grammatical_person_schedule,
    largest_remainder_allocation,
)
from easy_language_learning_tool.generation.prompts import build_batch_prompt


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
        self.assertEqual(settings(base_sentences=2_500, extra_forms=1).final_rows, 5_000)
        self.assertEqual(settings(base_sentences=5_000, extra_forms=0).final_rows, 5_000)
        with self.assertRaises(ValidationError):
            settings(base_sentences=2_501, extra_forms=1)
        with self.assertRaises(ValidationError):
            settings(base_sentences=1_000, extra_forms=5)

    def test_languages_must_differ(self) -> None:
        with self.assertRaises(ValidationError):
            settings(translation_language=Language.GERMAN)

    def test_thai_script_options_have_real_labels_and_shared_speech_locale(self) -> None:
        self.assertEqual(Language.THAI_SCRIPT.label, "Thai (Thai script)")
        self.assertEqual(Language.THAI_PAIBOON.label, "Thai (Paiboon romanization)")
        self.assertEqual(Language.THAI_SCRIPT.speech_locale, "th-TH")
        self.assertEqual(Language.THAI_PAIBOON.speech_locale, "th-TH")

    def test_thai_romanization_is_locked_in_generation_prompt(self) -> None:
        config = settings(
            learning_language=Language.THAI_PAIBOON,
            base_sentences=1,
            pronoun_change=0,
        )
        plan = build_generation_plan(config, [WordRecord(rank=1, lemma="sà-wàt-dii")])
        prompt = build_batch_prompt(config, list(plan))
        self.assertIn("tone-marked Paiboon romanization", prompt)
        self.assertIn("do not use Thai script", prompt)

    def test_pronoun_scale_zero_is_always_neutral(self) -> None:
        schedule = grammatical_person_schedule(100, 0, 77)
        self.assertEqual(schedule, (GrammaticalPerson.NEUTRAL,) * 100)

    def test_neutral_plan_is_explicit_in_generation_prompt(self) -> None:
        config = settings(base_sentences=1, pronoun_change=0)
        plan = build_generation_plan(config, [WordRecord(rank=1, lemma="Tag")])
        prompt = build_batch_prompt(config, list(plan))
        self.assertIn("neutral or impersonal sentence structure", prompt)
        self.assertIn('"grammatical_person":"neutral"', prompt)

    def test_pronoun_scale_uses_exact_twenty_percent_increments(self) -> None:
        for value in range(1, 5):
            with self.subTest(value=value):
                first = grammatical_person_schedule(100, value, 77)
                second = grammatical_person_schedule(100, value, 77)
                self.assertEqual(first, second)
                personal_count = sum(person is not GrammaticalPerson.NEUTRAL for person in first)
                self.assertEqual(personal_count, value * 20)

    def test_pronoun_scale_five_changes_every_sentence_and_includes_neutral(self) -> None:
        schedule = grammatical_person_schedule(70, 5, 77)
        self.assertIn(GrammaticalPerson.NEUTRAL, schedule)
        self.assertTrue(
            all(first is not second for first, second in zip(schedule, schedule[1:], strict=False))
        )

    def test_plan_applies_person_schedule_to_every_extra_form_row(self) -> None:
        config = settings(base_sentences=5, extra_forms=1, pronoun_change=5)
        words = [WordRecord(rank=index, lemma=f"word-{index}") for index in range(1, 6)]
        plan = build_generation_plan(config, words)
        self.assertTrue(
            all(
                first.grammatical_person is not second.grammatical_person
                for first, second in zip(plan, plan[1:], strict=False)
            )
        )

    def test_plan_expands_forms_and_keeps_base_attributes(self) -> None:
        config = settings(base_sentences=5, extra_forms=2, question_percentage=Decimal("40"))
        words = [WordRecord(rank=index, lemma=f"word-{index}") for index in range(1, 6)]
        plan = build_generation_plan(config, words)
        self.assertEqual(len(plan), 15)
        self.assertEqual(sum(row.form_index == 0 for row in plan), 5)
        self.assertEqual(
            sum(row.form_index == 0 and row.sentence_kind is SentenceKind.QUESTION for row in plan),
            2,
        )
        for offset in range(0, 15, 3):
            group = plan[offset : offset + 3]
            self.assertEqual(len({row.word.lemma for row in group}), 1)
            self.assertEqual(len({row.cefr_level for row in group}), 1)
            self.assertEqual([row.form_index for row in group], [0, 1, 2])

    def test_duplicate_base_lemmas_are_rejected(self) -> None:
        config = settings(base_sentences=2)
        words = [WordRecord(rank=1, lemma="gehen"), WordRecord(rank=2, lemma="Gehen")]
        with self.assertRaises(ValueError):
            build_generation_plan(config, words)


if __name__ == "__main__":
    unittest.main()
