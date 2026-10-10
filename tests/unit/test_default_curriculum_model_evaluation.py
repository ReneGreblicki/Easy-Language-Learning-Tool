import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/evaluate_default_deck_models.py"
spec = importlib.util.spec_from_file_location("curriculum_model_evaluation", SCRIPT)
assert spec and spec.loader
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_blind_order_is_deterministic_and_varies():
    models = ["gpt-4.1", "gpt-5.6-luna", "gpt-5.6-terra"]
    first = evaluation.blind_order("de-DE", 1, models)
    assert first == evaluation.blind_order("de-DE", 1, models)
    assert first != evaluation.blind_order("de-DE", 2, models)
    assert set(first) == set(models)


def test_weighted_score_uses_declared_rubric():
    row = {field: 5 for field in evaluation.SCORE_FIELDS}
    assert evaluation.weighted_score(row) == 100
    row["meaning"] = 1
    assert evaluation.weighted_score(row) == 72


def test_parse_inputs_rejects_single_model():
    try:
        evaluation.parse_inputs(["gpt-4.1=one.json"])
    except ValueError as error:
        assert "Exactly three" in str(error)
    else:
        raise AssertionError("Expected a validation error")


def test_summary_compares_models_within_each_concept():
    models = ["a", "b", "c"]
    curricula = {
        model: {
            "api_usage": {"total_tokens": index},
            "elapsed_seconds": index,
            "reasoning_effort": None,
        }
        for index, model in enumerate(models)
    }
    rows = []
    for concept_id in (1, 2):
        for index, model in enumerate(models):
            rows.append(
                {
                    "language": "en-US",
                    "concept_id": concept_id,
                    "model": model,
                    "fatal": False,
                    **{field: 5 - index for field in evaluation.SCORE_FIELDS},
                }
            )
    summary = evaluation.summarize(rows, curricula)
    assert summary["a"]["wins"] == 2
    assert summary["b"]["wins"] == 0
    assert summary["a"]["quality_score"] == 100
