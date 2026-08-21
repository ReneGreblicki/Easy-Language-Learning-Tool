from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field

from .models import TtsSettings


class TtsManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    workbook_checksum: str
    settings_checksum: str
    total_rows: int
    completed_rows: list[int] = Field(default_factory=list)
    state: str = "pending"
    last_error: str | None = None
    partial_mp3: str | None = None
    final_mp3: str | None = None


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def settings_checksum(settings: TtsSettings) -> str:
    return hashlib.sha256(settings.model_dump_json().encode("utf-8")).hexdigest()


def save_manifest(path: Path, manifest: TtsManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(manifest.model_dump_json(indent=2))
        temporary = Path(handle.name)
    temporary.replace(path)


def load_manifest(path: Path) -> TtsManifest | None:
    if not path.exists():
        return None
    return TtsManifest.model_validate_json(path.read_text(encoding="utf-8"))
