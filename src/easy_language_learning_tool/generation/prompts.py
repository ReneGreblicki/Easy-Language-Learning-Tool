from __future__ import annotations

import json
import random

from easy_language_learning_tool.domain.enums import CEFR_MAX_WORDS
from easy_language_learning_tool.domain.models import GenerationSettings, PlannedRow

OUTPUT_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rows"],
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "row_number",
                    "foreign_word",
                    "word_translation",
                    "foreign_sentence",
                    "sentence_translation",
                    "used_word_form",
                    "word_form_or_variant",
                ],
                "properties": {
                    "row_number": {"type": "integer"},
                    "foreign_word": {"type": "string"},
                    "word_translation": {"type": "string"},
                    "foreign_sentence": {"type": "string"},
                    "sentence_translation": {"type": "string"},
                    "used_word_form": {"type": "string"},
                    "word_form_or_variant": {"type": "string"},
                },
            },
        }
    },
}


def _preferred_form(plan: PlannedRow) -> str:
    if plan.form_index == 0:
        return plan.word.lemma
    alternatives = sorted(
        {
            form.strip()
            for form in plan.word.forms
            if form.strip() and form.casefold().strip() != plan.word.lemma.casefold().strip()
        },
        key=str.casefold,
    )
    random.Random(f"{plan.seed}:{plan.word.rank}").shuffle(alternatives)
    offset = plan.form_index - 1
    return alternatives[offset] if offset < len(alternatives) else ""


def build_batch_prompt(settings: GenerationSettings, plans: list[PlannedRow]) -> str:
    tasks = [
        {
            "row_number": plan.row_number,
            "lemma": plan.word.lemma,
            "part_of_speech": plan.word.part_of_speech,
            "known_forms": plan.word.forms,
            "preferred_surface_form": _preferred_form(plan),
            "baseline_translation": plan.word.translation,
            "cefr": plan.cefr_level.value,
            "maximum_words": CEFR_MAX_WORDS[plan.cefr_level],
            "sentence_kind": plan.sentence_kind.value,
            "grammatical_person": plan.grammatical_person.value,
            "form_index": plan.form_index,
        }
        for plan in plans
    ]
    return (
        "Create formal, standard language-learning examples. The learning language is "
        f"{settings.learning_language.label}; translate accurately and directly into "
        f"{settings.translation_language.label}. Use every assigned word naturally and preserve its "
        "assigned part of speech. If it is 'unknown', infer the most natural part of speech for "
        "the requested sentence and report a valid form/variant. For verbs, vary tense, mood, person, or participle; for nouns, "
        "vary number or case where the language supports it; for adjectives, determiners, and "
        "pronouns, vary agreement, case, or comparison where valid. "
        "Each sentence must stand alone, make sense without context, obey its exact question/statement "
        "type and maximum word count, and avoid slang. Extra-form rows (form_index > 0) must use a "
        "different valid grammatical form from the original. Use preferred_surface_form when it "
        "is non-empty. If the word is invariant or has too "
        "few distinct forms, keep the valid surface form but use a clearly different standalone "
        "context and label it invariant-context-N. Return only the required JSON.\n"
        f"TASKS={json.dumps(tasks, ensure_ascii=False, separators=(',', ':'))}"
    )
