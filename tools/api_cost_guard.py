"""Small, dependency-free cost guards for paid curriculum tooling."""

from __future__ import annotations

from dataclasses import dataclass

# Standard API prices in USD per million tokens. Keep this table pinned and review it
# before changing models; provider billing remains authoritative.
MODEL_PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6-sol": (2.00, 10.00),
    "gpt-6-astra": (10.00, 50.00),
}


def token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return the conservative uncached standard-price estimate for one response."""
    if model not in MODEL_PRICES:
        raise ValueError(f"No pinned price for {model!r}; add and review it before paid use")
    input_price, output_price = MODEL_PRICES[model]
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def approximate_prompt_tokens(payload_bytes: bytes) -> int:
    """Conservatively estimate multilingual JSON input tokens before a request."""
    return max(1, (len(payload_bytes) + 2) // 3)


@dataclass
class CostBudget:
    maximum_usd: float
    spent_usd: float = 0.0

    def preflight(self, model: str, payload_bytes: bytes, max_completion_tokens: int) -> None:
        projected = token_cost(
            model,
            approximate_prompt_tokens(payload_bytes),
            max_completion_tokens,
        )
        if self.spent_usd + projected > self.maximum_usd + 1e-9:
            raise RuntimeError(
                "Paid API budget would be exceeded before the next request: "
                f"spent=${self.spent_usd:.4f}, reserve=${projected:.4f}, "
                f"limit=${self.maximum_usd:.4f}, model={model}"
            )

    def record(self, model: str, usage: dict) -> float:
        cost = token_cost(
            model,
            int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)),
        )
        self.spent_usd += cost
        if self.spent_usd > self.maximum_usd + 1e-9:
            raise RuntimeError(
                "Paid API budget was exceeded by the completed request: "
                f"spent=${self.spent_usd:.4f}, limit=${self.maximum_usd:.4f}"
            )
        return cost
