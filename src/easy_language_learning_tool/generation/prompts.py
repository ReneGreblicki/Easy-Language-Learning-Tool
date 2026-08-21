from __future__ import annotations

import json

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
                    "foreign_verb",
                    "verb_translation",
                    "foreign_sentence",
                    "sentence_translation",
                    "used_verb_form",
                    "tense_or_form",
                ],
                "properties": {
                    "row_number": {"type": "integer"},
                    "foreign_verb": {"type": "string"},
                    "verb_translation": {"type": "string"},
                    "foreign_sentence": {"type": "string"},
                    "sentence_translation": {"type": "string"},
                    "used_verb_form": {"type": "string"},
                    "tense_or_form": {"type": "string"},
                },
            },
        }
    },
}


def build_batch_prompt(settings: GenerationSettings, plans: list[PlannedRow]) -> str:
    tasks = [
        {
            "row_number": plan.row_number,
            "lemma": plan.verb.lemma,
            "baseline_translation": plan.verb.translation,
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
        f"{settings.translation_language.label}. Use every assigned lemma in a valid inflected form. "
        "Each sentence must stand alone, make sense without context, obey its exact question/statement "
        "type and maximum word count, and avoid slang. Extra-form rows (form_index > 0) must use a "
        "different valid tense, mood, or construction from the original. Return only the required JSON.\n"
        f"TASKS={json.dumps(tasks, ensure_ascii=False, separators=(',', ':'))}"
    )
