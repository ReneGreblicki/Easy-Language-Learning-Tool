import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import deploy_default_decks as deploy


def valid_database():
    return {
        "missing_tables": [],
        "default_table_rls": {"default_decks": True},
        "catalog": [{"decks": 72, "languages": 24, "published_decks": 0}],
        "versions": [],
    }


def run_deploy(monkeypatch, tmp_path, state):
    monkeypatch.setattr(deploy, "inspect_database", lambda: state)
    monkeypatch.setattr(
        sys,
        "argv",
        ["deploy", "--deploy", str(tmp_path), "--report", str(tmp_path / "report.json")],
    )

    def no_write(*args, **kwargs):
        pytest.fail("Database write must not occur after a failed preflight")

    monkeypatch.setattr(deploy, "query", no_write)
    monkeypatch.setattr(deploy, "publish_transaction", no_write)
    deploy.main()


def test_refuses_preexisting_published_version(monkeypatch, tmp_path):
    state = valid_database()
    state["versions"] = [{"content_version": 1, "rows": 24000}]
    with pytest.raises(AssertionError, match="Existing content"):
        run_deploy(monkeypatch, tmp_path, state)


def test_refuses_unapproved_curriculum(monkeypatch, tmp_path):
    (tmp_path / "curriculum.json").write_text("modified")
    with pytest.raises(AssertionError, match="Unapproved curriculum"):
        run_deploy(monkeypatch, tmp_path, valid_database())


def test_refuses_missing_rls(monkeypatch, tmp_path):
    state = valid_database()
    state["default_table_rls"]["default_decks"] = False
    with pytest.raises(AssertionError, match="RLS"):
        run_deploy(monkeypatch, tmp_path, state)


def test_wrong_project_is_rejected_before_credentials_or_network(monkeypatch):
    monkeypatch.setenv("PROJECT_REF", "wrong-project")
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    with pytest.raises(AssertionError, match="Unexpected deployment target"):
        deploy.query("select 1")
