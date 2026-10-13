import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/audit_default_deck_curriculum.py"
spec = importlib.util.spec_from_file_location("curriculum_audit", SCRIPT)
assert spec and spec.loader
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


def test_audit_detects_script_and_meaning_errors(tmp_path):
    curriculum = tmp_path / "curriculum.json"
    curriculum.write_text(
        """{
          "pilot": true,
          "languages": {
            "en-US": [{"id": 1, "level": "A1", "word": "the",
              "sentence": "The cat sleeps.", "sense": "specific article", "source_rank": 1}],
            "ru-RU": [{"id": 1, "level": "A1", "word": "the",
              "sentence": "The cat sleeps.", "sense": "different", "source_rank": null}]
          }
        }""",
        encoding="utf-8",
    )
    result = audit_module.audit(curriculum)
    assert any("level counts" in error for error in result["errors"])
    assert any("expected script" in error for error in result["errors"])
    assert any("meanings drifted" in error for error in result["errors"])
