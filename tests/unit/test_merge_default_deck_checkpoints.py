import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/merge_default_deck_checkpoints.py"
spec = importlib.util.spec_from_file_location("merge_default_deck_checkpoints", SCRIPT)
assert spec and spec.loader
merger = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = merger
spec.loader.exec_module(merger)


def write_batch(directory: Path, code: str, digest: str, ids: list[int], marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{code}-{digest}.json"
    path.write_text(json.dumps([{"id": row_id, "marker": marker} for row_id in ids]))
    return path


def test_merge_preserves_existing_files_and_unions_rows(tmp_path):
    destination = tmp_path / "destination"
    new = tmp_path / "new"
    old = tmp_path / "old"
    digest = "a" * 20
    write_batch(destination, "en-US", digest, [1], "current")
    write_batch(new, "en-US", digest, [1], "new-conflict")
    write_batch(new, "es-ES", "b" * 20, [1, 2], "new")
    write_batch(old, "es-ES", "c" * 20, [2, 3], "old")

    report = merger.merge_checkpoints(destination, [new, old])
    inventory = merger.checkpoint_inventory(destination)

    assert report == {"copied_files": 2, "preserved_collisions": 1}
    assert json.loads((destination / f"en-US-{digest}.json").read_text())[0]["marker"] == "current"
    assert inventory["raw_rows"] == 4
    assert inventory["languages"]["es-ES"]["rows"] == 3
