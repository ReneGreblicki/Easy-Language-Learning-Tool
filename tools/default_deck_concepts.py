"""Deterministic source selection and English-content checks for default decks."""

from __future__ import annotations

import re
import unicodedata

DEFAULT_CONCEPT_COUNT = 1_000
ALLOWED_ONE_LETTER_WORDS = {"a", "i"}
EXCLUDED_ENGLISH_TOKENS = {
    "al",
    "co",
    "de",
    "dr",
    "etc",
    "la",
    "lol",
    "mr",
    "non",
    "re",
    "st",
    "tv",
    "uk",
}
META_USAGE_PATTERNS = (
    re.compile(r"\b(?:abbreviation|acronym|initial|postal code|state code|short code)\b", re.I),
    re.compile(r"\b(?:stands for|is a code for|is short for)\b", re.I),
    re.compile(r"\b(?:the letter|the symbol)\b", re.I),
)
WORD_PATTERN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+)*")


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def english_source_issue(value: str) -> str | None:
    """Reject fragments and metadata tokens while retaining ordinary short words."""
    word = unicodedata.normalize("NFKC", value).strip()
    key = normalized(word)
    if not word or not WORD_PATTERN.fullmatch(word):
        return "not a standalone Latin-script word"
    if len(key) == 1 and key not in ALLOWED_ONE_LETTER_WORDS:
        return "isolated letter or token fragment"
    if key in EXCLUDED_ENGLISH_TOKENS:
        return "abbreviation, foreign fragment, code, or non-word"
    return None


def select_english_concepts(
    rows: list[dict], count: int = DEFAULT_CONCEPT_COUNT
) -> tuple[list[dict], list[dict]]:
    """Keep valid raw slots and backfill rejected slots with the next valid unused words."""
    if len(rows) < count:
        raise ValueError(f"Expected at least {count} ranked English source rows")
    selected: list[dict] = []
    replacements: list[dict] = []
    used: set[str] = set()
    pool_index = count

    def next_replacement() -> dict:
        nonlocal pool_index
        while pool_index < len(rows):
            candidate = rows[pool_index]
            pool_index += 1
            key = normalized(str(candidate.get("lemma", "")))
            if key not in used and english_source_issue(str(candidate.get("lemma", ""))) is None:
                return candidate
        raise ValueError(
            "The ranked English corpus does not contain enough valid replacement words"
        )

    for concept_id, original in enumerate(rows[:count], 1):
        original_word = str(original.get("lemma", ""))
        original_key = normalized(original_word)
        issue = english_source_issue(original_word)
        duplicate = original_key in used
        chosen = original
        if issue or duplicate:
            chosen = next_replacement()
            replacements.append(
                {
                    "id": concept_id,
                    "removed_word": original_word,
                    "removed_source_rank": original.get("rank"),
                    "reason": issue or "duplicate after normalization",
                    "replacement_word": chosen["lemma"],
                    "replacement_source_rank": chosen["rank"],
                }
            )
        key = normalized(str(chosen["lemma"]))
        used.add(key)
        selected.append(
            {
                **chosen,
                "concept_id": concept_id,
                "raw_slot_rank": original.get("rank"),
                "replaced_raw_word": original_word if chosen is not original else None,
            }
        )
    if len(selected) != count or len({row["concept_id"] for row in selected}) != count:
        raise ValueError("Clean English concept selection did not produce stable unique IDs")
    return selected, replacements


def english_usage_issues(word: str, sentence: str, sense: str) -> list[str]:
    """Return deterministic reasons an English learning row requires revision."""
    issues: list[str] = []
    source_issue = english_source_issue(word)
    if source_issue:
        issues.append(source_issue)
    sentence_key = normalized(sentence)
    word_key = normalized(word)
    if word_key and not re.search(rf"(?<!\w){re.escape(word_key)}(?!\w)", sentence_key):
        issues.append("target word is absent from the sentence")
    combined = sentence + " " + sense
    if any(pattern.search(combined) for pattern in META_USAGE_PATTERNS):
        issues.append("meta-language, code, or abbreviation example")
    if len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", sentence)) < 3:
        issues.append("sentence is too short to demonstrate natural usage")
    return issues
