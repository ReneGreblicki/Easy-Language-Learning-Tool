from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from easy_language_learning_tool.domain.enums import CEFR_MAX_WORDS, SentenceKind
from easy_language_learning_tool.domain.models import PlannedRow

WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)


class GeneratedSentence(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int = Field(ge=1)
    foreign_verb: str = Field(min_length=1, max_length=120)
    verb_translation: str = Field(min_length=1, max_length=200)
    foreign_sentence: str = Field(min_length=1, max_length=1_000)
    sentence_translation: str = Field(min_length=1, max_length=2_000)
    used_verb_form: str = Field(min_length=1, max_length=120)
    tense_or_form: str = Field(min_length=1, max_length=120)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class SentenceValidator:
    def validate(
        self, sentence: GeneratedSentence, plan: PlannedRow
    ) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        if sentence.row_number != plan.row_number:
            issues.append(
                ValidationIssue(code="row_number", message="Returned row number is incorrect.")
            )
        if sentence.foreign_verb.casefold().strip() != plan.verb.lemma.casefold().strip():
            issues.append(
                ValidationIssue(code="lemma", message="Returned lemma differs from the plan.")
            )
        if (
            plan.verb.translation
            and sentence.verb_translation.casefold().strip()
            != plan.verb.translation.casefold().strip()
        ):
            issues.append(
                ValidationIssue(
                    code="verb_translation",
                    message="Verb translation differs from the ranked dataset.",
                )
            )
        words = WORD_PATTERN.findall(sentence.foreign_sentence)
        maximum = CEFR_MAX_WORDS[plan.cefr_level]
        if len(words) > maximum:
            issues.append(
                ValidationIssue(
                    code="word_count",
                    message=f"Sentence has {len(words)} words; {maximum} allowed for {plan.cefr_level}.",
                )
            )
        used_form = sentence.used_verb_form.casefold().strip()
        if used_form not in sentence.foreign_sentence.casefold():
            issues.append(
                ValidationIssue(
                    code="verb_form", message="The declared verb form is absent from the sentence."
                )
            )
        if plan.form_index > 0 and sentence.tense_or_form.casefold() in {"base", "original"}:
            issues.append(
                ValidationIssue(
                    code="extra_form", message="An extra row must use a different verb form."
                )
            )
        is_question = sentence.foreign_sentence.rstrip().endswith("?")
        if plan.sentence_kind is SentenceKind.QUESTION and not is_question:
            issues.append(
                ValidationIssue(
                    code="sentence_kind", message="The planned question lacks a question mark."
                )
            )
        if plan.sentence_kind is SentenceKind.STATEMENT and is_question:
            issues.append(
                ValidationIssue(
                    code="sentence_kind",
                    message="The planned statement is formatted as a question.",
                )
            )
        if not sentence.sentence_translation.strip():
            issues.append(
                ValidationIssue(code="translation", message="Sentence translation is empty.")
            )
        return tuple(issues)
