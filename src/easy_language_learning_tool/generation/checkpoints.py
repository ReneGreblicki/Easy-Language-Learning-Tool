from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field

from easy_language_learning_tool.domain.models import GenerationSettings
from easy_language_learning_tool.validation.sentences import GeneratedSentence


class GenerationCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings_checksum: str
    provider: str
    model: str
    completed_rows: list[GeneratedSentence] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


def settings_checksum(settings: GenerationSettings, provider: str, model: str) -> str:
    payload = settings.model_dump_json() + "|" + provider + "|" + model
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_checkpoint(path: Path, checkpoint: GenerationCheckpoint) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(checkpoint.model_dump_json(indent=2))
        temporary = Path(handle.name)
    temporary.replace(path)


def load_checkpoint(path: Path) -> GenerationCheckpoint | None:
    if not path.exists():
        return None
    return GenerationCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))
