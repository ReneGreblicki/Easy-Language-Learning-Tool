from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from easy_language_learning_tool.domain.enums import CEFR_MAX_WORDS, SentenceKind
from easy_language_learning_tool.domain.models import PlannedRow

WORD_PATTERN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)


class GeneratedSentence(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int = Field(ge=1)
    foreign_word: str = Field(min_length=1, max_length=120)
    word_translation: str = Field(min_length=1, max_length=200)
    foreign_sentence: str = Field(min_length=1, max_length=1_000)
    sentence_translation: str = Field(min_length=1, max_length=2_000)
    used_word_form: str = Field(min_length=1, max_length=120)
    word_form_or_variant: str = Field(min_length=1, max_length=120)


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
        if sentence.foreign_word.casefold().strip() != plan.word.lemma.casefold().strip():
            issues.append(
                ValidationIssue(code="lemma", message="Returned lemma differs from the plan.")
            )
        if (
            plan.word.translation
            and sentence.word_translation.casefold().strip()
            != plan.word.translation.casefold().strip()
        ):
            issues.append(
                ValidationIssue(
                    code="word_translation",
                    message="Word translation differs from the ranked dataset.",
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
        used_form = sentence.used_word_form.casefold().strip()
        if used_form not in sentence.foreign_sentence.casefold():
            issues.append(
                ValidationIssue(
                    code="word_form", message="The declared word form is absent from the sentence."
                )
            )
        if plan.form_index > 0 and sentence.word_form_or_variant.casefold() in {"base", "original"}:
            issues.append(
                ValidationIssue(
                    code="extra_form",
                    message="An extra row must use a different form or invariant context.",
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
