from tools.default_deck_concepts import english_usage_issues, select_english_concepts


def alpha_word(index: int) -> str:
    value = index
    suffix = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        suffix = chr(97 + remainder) + suffix
    return "term" + suffix


def test_invalid_raw_slot_is_backfilled_without_changing_concept_id():
    rows = [{"rank": rank, "lemma": alpha_word(rank), "source": "test"} for rank in range(1, 1003)]
    rows[571]["lemma"] = "de"

    selected, replacements = select_english_concepts(rows)

    assert len(selected) == 1000
    assert selected[571]["concept_id"] == 572
    assert selected[571]["lemma"] == alpha_word(1001)
    assert selected[571]["rank"] == 1001
    assert replacements == [
        {
            "id": 572,
            "removed_word": "de",
            "removed_source_rank": 572,
            "reason": "abbreviation, foreign fragment, code, or non-word",
            "replacement_word": alpha_word(1001),
            "replacement_source_rank": 1001,
        }
    ]


def test_english_usage_rejects_meta_code_examples():
    issues = english_usage_issues(
        "de",
        "The form uses de as a short code for Delaware.",
        "an abbreviation for Delaware",
    )
    assert "abbreviation, foreign fragment, code, or non-word" in issues
    assert "meta-language, code, or abbreviation example" in issues
