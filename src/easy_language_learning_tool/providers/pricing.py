from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class PricingEntry:
    provider: str
    model: str
    input_per_million_usd: Decimal
    output_per_million_usd: Decimal
    source: str
    updated: str


@dataclass(frozen=True)
class CostEstimate:
    rows: int
    usd: Decimal | None
    assumption: str


class PricingRegistry:
    def __init__(self, entries: list[PricingEntry]) -> None:
        self._entries = {(entry.provider.casefold(), entry.model): entry for entry in entries}

    @classmethod
    def from_json(cls, path: Path) -> PricingRegistry:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls(
            [
                PricingEntry(
                    provider=item["provider"],
                    model=item["model"],
                    input_per_million_usd=Decimal(str(item["input_per_million_usd"])),
                    output_per_million_usd=Decimal(str(item["output_per_million_usd"])),
                    source=item["source"],
                    updated=item["updated"],
                )
                for item in raw.get("models", [])
            ]
        )

    def get(self, provider: str, model: str) -> PricingEntry | None:
        return self._entries.get((provider.casefold(), model))

    def estimate(
        self,
        provider: str,
        model: str,
        rows: int,
        *,
        input_tokens_per_row: int = 90,
        output_tokens_per_row: int = 45,
    ) -> CostEstimate:
        if provider.casefold() == "ollama":
            return CostEstimate(
                rows, Decimal("0"), "API cost only; local hardware/electricity excluded"
            )
        entry = self.get(provider, model)
        assumption = (
            f"{input_tokens_per_row} input and {output_tokens_per_row} output tokens per row"
        )
        if entry is None:
            return CostEstimate(rows, None, assumption)
        cost = (
            Decimal(rows * input_tokens_per_row) * entry.input_per_million_usd
            + Decimal(rows * output_tokens_per_row) * entry.output_per_million_usd
        ) / Decimal(1_000_000)
        return CostEstimate(rows, cost.quantize(Decimal("0.0001")), assumption)

    def comparison(
        self,
        provider: str,
        model: str,
        current_rows: int,
    ) -> tuple[CostEstimate, ...]:
        counts = [1_000, 2_000, 3_000, 4_000]
        if current_rows not in counts:
            counts.append(current_rows)
        return tuple(self.estimate(provider, model, count) for count in counts)

    def actual_from_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Decimal | None:
        if provider.casefold() == "ollama":
            return Decimal("0")
        entry = self.get(provider, model)
        if entry is None:
            return None
        cost = (
            Decimal(input_tokens) * entry.input_per_million_usd
            + Decimal(output_tokens) * entry.output_per_million_usd
        ) / Decimal(1_000_000)
        return cost.quantize(Decimal("0.0001"))
