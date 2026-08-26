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


def grammatical_person_schedule(
    sentence_count: int,
    change_value: int,
    seed: int,
) -> tuple[GrammaticalPerson, ...]:
    """Return a deterministic neutral/personal sentence-subject schedule.

    Values 0–4 assign exactly 0%, 20%, 40%, 60%, or 80% of rows to a
    randomly selected grammatical person, with the remainder kept neutral.
    Value 5 varies every consecutive row across neutral and personal patterns.
    """
    if sentence_count < 1:
        raise ValueError("Sentence count must be positive.")
    if change_value not in range(6):
        raise ValueError("Pronoun-change value must be from 0 to 5.")

    rng = random.Random(seed)
    personal_people = [
        person for person in GrammaticalPerson if person is not GrammaticalPerson.NEUTRAL
    ]
    if change_value == 0:
        return (GrammaticalPerson.NEUTRAL,) * sentence_count

    if change_value == 5:
        people = list(GrammaticalPerson)
        result: list[GrammaticalPerson] = []
        while len(result) < sentence_count:
            rng.shuffle(people)
            if result and people[0] is result[-1]:
                swap_index = next(
                    index for index, person in enumerate(people[1:], 1) if person is not result[-1]
                )
                people[0], people[swap_index] = people[swap_index], people[0]
            result.extend(people)
        return tuple(result[:sentence_count])

    counts = largest_remainder_allocation(
        sentence_count,
        {
            "neutral": 5 - change_value,
            "personal": change_value,
        },
        ("neutral", "personal"),
    )
    personal_positions = set(rng.sample(range(sentence_count), counts["personal"]))
    return tuple(
        rng.choice(personal_people) if index in personal_positions else GrammaticalPerson.NEUTRAL
        for index in range(sentence_count)
    )
