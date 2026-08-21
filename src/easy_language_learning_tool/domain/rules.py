from __future__ import annotations

import random
from collections.abc import Mapping
from decimal import ROUND_FLOOR, Decimal

from .enums import GrammaticalPerson


def largest_remainder_allocation[T](
    total: int,
    weights: Mapping[T, Decimal | int | float],
    order: tuple[T, ...] | list[T],
) -> dict[T, int]:
    """Allocate an integer total deterministically using Hamilton's method."""
    if total < 0:
        raise ValueError("Total cannot be negative.")
    ordered = list(order)
    if set(weights) != set(ordered) or len(weights) != len(ordered):
        raise ValueError("Weights and allocation order must contain the same unique keys.")
    decimal_weights = {key: Decimal(str(weights[key])) for key in ordered}
    if any(value < 0 for value in decimal_weights.values()):
        raise ValueError("Weights cannot be negative.")
    weight_total = sum(decimal_weights.values())
    if weight_total <= 0:
        raise ValueError("At least one weight must be positive.")

    quotas = {key: Decimal(total) * decimal_weights[key] / weight_total for key in ordered}
    allocated = {key: int(quotas[key].to_integral_value(rounding=ROUND_FLOOR)) for key in ordered}
    remaining = total - sum(allocated.values())
    order_index = {key: index for index, key in enumerate(ordered)}
    ranked = sorted(
        ordered,
        key=lambda key: (-(quotas[key] - allocated[key]), order_index[key]),
    )
    for key in ranked[:remaining]:
        allocated[key] += 1
    return allocated


def pronoun_cadence_size(value: int, base_count: int) -> int:
    if value == 1:
        return base_count
    return {2: 20, 3: 10, 4: 3, 5: 1}[value]


def grammatical_person_schedule(
    base_count: int,
    cadence_value: int,
    seed: int,
) -> tuple[GrammaticalPerson, ...]:
    if base_count < 1:
        raise ValueError("Base count must be positive.")
    if cadence_value not in range(1, 6):
        raise ValueError("Pronoun-change value must be from 1 to 5.")
    cadence = pronoun_cadence_size(cadence_value, base_count)
    rng = random.Random(seed)
    people = list(GrammaticalPerson)
    current = rng.choice(people)
    result: list[GrammaticalPerson] = []
    for index in range(base_count):
        if index and index % cadence == 0:
            current = rng.choice([person for person in people if person is not current])
        result.append(current)
    return tuple(result)
