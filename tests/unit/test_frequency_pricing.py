from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path

from easy_language_learning_tool.domain.enums import Language
from easy_language_learning_tool.domain.frequency import FrequencyRepository
from easy_language_learning_tool.providers.pricing import PricingEntry, PricingRegistry


class FrequencyAndPricingTests(unittest.TestCase):
    def test_frequency_selection_is_ranked_unique_and_translated(self) -> None:
        source = Path(__file__).parents[2] / "resources" / "frequency_data" / "demo" / "verbs.jsonl"
        repository = FrequencyRepository.from_jsonl(source)
        rows = repository.select(Language.GERMAN, Language.US_ENGLISH, 3)
        self.assertEqual([row.lemma for row in rows], ["sein", "haben", "werden"])
        self.assertEqual(rows[0].translation, "to be")

    def test_release_readiness_reports_demo_shortfall(self) -> None:
        source = Path(__file__).parents[2] / "resources" / "frequency_data" / "demo" / "verbs.jsonl"
        errors = FrequencyRepository.from_jsonl(source).validate_release_readiness(10)
        self.assertEqual(len(errors), 5)

    def test_pricing_estimate_and_unknown_fallback(self) -> None:
        registry = PricingRegistry(
            [PricingEntry("Provider", "model", Decimal("1"), Decimal("2"), "source", "date")]
        )
        known = registry.estimate(
            "Provider", "model", 1_000, input_tokens_per_row=100, output_tokens_per_row=50
        )
        unknown = registry.estimate("Provider", "other", 1_000)
        self.assertEqual(known.usd, Decimal("0.2000"))
        self.assertIsNone(unknown.usd)
        self.assertEqual(
            registry.actual_from_usage("Provider", "model", 100_000, 50_000),
            Decimal("0.2000"),
        )
        self.assertIsNone(registry.actual_from_usage("Provider", "other", 1, 1))


if __name__ == "__main__":
    unittest.main()
