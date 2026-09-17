from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FUNCTION = REPOSITORY_ROOT / "supabase" / "functions" / "generate-deck" / "index.ts"
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "supabase-generation-deploy.yml"
MIGRATION = (
    REPOSITORY_ROOT
    / "supabase"
    / "migrations"
    / "0005_generation_optimization_metrics.sql"
)


class GenerationOptimizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.function_source = FUNCTION.read_text(encoding="utf-8")
        cls.workflow_source = WORKFLOW.read_text(encoding="utf-8")
        cls.migration_source = MIGRATION.read_text(encoding="utf-8")

    def test_gpt_4o_mini_is_the_generation_primary(self) -> None:
        self.assertIn(
            'Deno.env.get("OPENAI_GENERATION_MODEL") ?? "gpt-4o-mini"',
            self.function_source,
        )
        self.assertIn('OPENAI_GENERATION_MODEL="gpt-4o-mini"', self.workflow_source)

    def test_recommendation_model_is_independent(self) -> None:
        self.assertIn('OPENAI_MODEL="$recommendation_model"', self.workflow_source)
        self.assertIn("OPENAI_GENERATION_FALLBACK_MODEL", self.function_source)

    def test_quality_gates_and_selective_fallback_are_enabled(self) -> None:
        self.assertIn("validateGeneratedRows", self.function_source)
        self.assertIn("generateWithFallback", self.function_source)
        self.assertIn("Quality validation failed", self.function_source)
        self.assertIn('attempt < 2', self.function_source)

    def test_optimized_batching_is_enabled(self) -> None:
        self.assertIn("const batchSize = 24;", self.function_source)
        self.assertIn("const parallelBatches = 6;", self.function_source)

    def test_generation_telemetry_is_persisted(self) -> None:
        for field in (
            "used_fallback",
            "attempt_count",
            "accepted_rows",
            "input_tokens",
            "output_tokens",
            "latency_ms",
            "validation_errors",
        ):
            self.assertIn(field, self.function_source)
            self.assertIn(field, self.migration_source)


if __name__ == "__main__":
    unittest.main()
