from __future__ import annotations

from decimal import Decimal

from .enums import CefrMode, SentenceKind
from .models import GenerationSettings, PlannedRow, VerbRecord
from .rules import grammatical_person_schedule, largest_remainder_allocation


def build_generation_plan(
    settings: GenerationSettings,
    ranked_verbs: list[VerbRecord],
) -> tuple[PlannedRow, ...]:
    """Build the complete deterministic row plan before any LLM call is made."""
    if len(ranked_verbs) < settings.base_sentences:
        raise ValueError("The ranked verb list does not contain enough unique verbs.")
    selected_verbs = ranked_verbs[: settings.base_sentences]
    normalized = [verb.lemma.casefold().strip() for verb in selected_verbs]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Base verb lemmas must be unique before list exhaustion.")

    levels = settings.cefr.ordered_levels()
    if settings.cefr.mode is CefrMode.SINGLE:
        cefr_counts = {levels[0]: settings.base_sentences}
    else:
        cefr_counts = largest_remainder_allocation(
            settings.base_sentences,
            settings.cefr.percentages,
            levels,
        )
    cefr_schedule = tuple(level for level in levels for _ in range(cefr_counts[level]))

    kind_counts = largest_remainder_allocation(
        settings.base_sentences,
        {
            SentenceKind.QUESTION: settings.question_percentage,
            SentenceKind.STATEMENT: Decimal("100") - settings.question_percentage,
        },
        (SentenceKind.QUESTION, SentenceKind.STATEMENT),
    )
    kind_schedule = (SentenceKind.QUESTION,) * kind_counts[SentenceKind.QUESTION] + (
        SentenceKind.STATEMENT,
    ) * kind_counts[SentenceKind.STATEMENT]
    people = grammatical_person_schedule(
        settings.base_sentences,
        settings.pronoun_change,
        settings.seed,
    )

    rows: list[PlannedRow] = []
    for base_index, verb in enumerate(selected_verbs):
        for form_index in range(settings.extra_forms + 1):
            rows.append(
                PlannedRow(
                    row_number=len(rows) + 1,
                    base_index=base_index + 1,
                    form_index=form_index,
                    verb=verb,
                    cefr_level=cefr_schedule[base_index],
                    sentence_kind=kind_schedule[base_index],
                    grammatical_person=people[base_index],
                    seed=settings.seed,
                )
            )
    return tuple(rows)
