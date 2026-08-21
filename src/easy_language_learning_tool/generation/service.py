from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from easy_language_learning_tool.domain.models import GenerationSettings, PlannedRow
from easy_language_learning_tool.providers.base import ProviderAdapter
from easy_language_learning_tool.validation.sentences import GeneratedSentence, SentenceValidator

from .checkpoints import (
    GenerationCheckpoint,
    load_checkpoint,
    save_checkpoint,
    settings_checksum,
)
from .prompts import OUTPUT_SCHEMA, build_batch_prompt

ProgressCallback = Callable[[int, int], None]


class GenerationService:
    def __init__(
        self, provider: ProviderAdapter, validator: SentenceValidator | None = None
    ) -> None:
        self.provider = provider
        self.validator = validator or SentenceValidator()

    async def generate(
        self,
        *,
        settings: GenerationSettings,
        plan: tuple[PlannedRow, ...],
        model: str,
        checkpoint_path: Path,
        batch_size: int = 20,
        retries: int = 2,
        progress: ProgressCallback | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> GenerationCheckpoint:
        checksum = settings_checksum(settings, self.provider.provider_name, model)
        checkpoint = load_checkpoint(checkpoint_path)
        if checkpoint is not None and checkpoint.settings_checksum != checksum:
            raise ValueError("The saved generation checkpoint does not match these settings.")
        if checkpoint is None:
            checkpoint = GenerationCheckpoint(
                settings_checksum=checksum,
                provider=self.provider.provider_name,
                model=model,
            )
        completed = list(checkpoint.completed_rows)
        completed_numbers = {row.row_number for row in completed}
        remaining = [row for row in plan if row.row_number not in completed_numbers]
        input_tokens = checkpoint.input_tokens
        output_tokens = checkpoint.output_tokens

        for start in range(0, len(remaining), batch_size):
            if cancel_event is not None and cancel_event.is_set():
                break
            batch = remaining[start : start + batch_size]
            accepted, usage_in, usage_out = await self._generate_batch(
                settings, batch, model, retries
            )
            completed.extend(accepted)
            completed.sort(key=lambda row: row.row_number)
            input_tokens += usage_in
            output_tokens += usage_out
            checkpoint = GenerationCheckpoint(
                settings_checksum=checksum,
                provider=self.provider.provider_name,
                model=model,
                completed_rows=completed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            save_checkpoint(checkpoint_path, checkpoint)
            if progress:
                progress(len(completed), len(plan))
        return checkpoint

    async def _generate_batch(
        self,
        settings: GenerationSettings,
        plans: list[PlannedRow],
        model: str,
        retries: int,
    ) -> tuple[list[GeneratedSentence], int, int]:
        pending = plans
        accepted: dict[int, GeneratedSentence] = {}
        input_tokens = 0
        output_tokens = 0
        last_errors: dict[int, str] = {}
        for _attempt in range(retries + 1):
            response = await self.provider.generate(
                model,
                build_batch_prompt(settings, pending),
                OUTPUT_SCHEMA,
            )
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            returned: dict[int, GeneratedSentence] = {}
            for raw in response.rows:
                try:
                    parsed_row = GeneratedSentence.model_validate(raw)
                    returned[parsed_row.row_number] = parsed_row
                except Exception:
                    continue
            next_pending: list[PlannedRow] = []
            for plan in pending:
                candidate = returned.get(plan.row_number)
                if candidate is None:
                    last_errors[plan.row_number] = "missing or structurally invalid row"
                    next_pending.append(plan)
                    continue
                issues = self.validator.validate(candidate, plan)
                if issues:
                    last_errors[plan.row_number] = "; ".join(issue.message for issue in issues)
                    next_pending.append(plan)
                else:
                    accepted[plan.row_number] = candidate
            pending = next_pending
            if not pending:
                return [accepted[plan.row_number] for plan in plans], input_tokens, output_tokens
        detail = ", ".join(f"row {number}: {message}" for number, message in last_errors.items())
        raise RuntimeError(f"Generation validation failed after retries: {detail}")
