from __future__ import annotations

from easy_language_learning_tool.domain.enums import Language
from tools.build_multisource_frequency_data import merge_rankings, valid_term


def test_all_requested_languages_have_stable_labels_and_locales() -> None:
    expected = {
        Language.POLISH: ("Polish", "pl-PL"),
        Language.DUTCH: ("Dutch", "nl-NL"),
        Language.DANISH: ("Danish", "da-DK"),
        Language.CROATIAN: ("Croatian", "hr-HR"),
        Language.VIETNAMESE: ("Vietnamese", "vi-VN"),
        Language.SIMPLIFIED_CHINESE: ("Chinese (Simplified)", "zh-CN"),
        Language.MALAYALAM: ("Malayalam", "ml-IN"),
        Language.SLOVAK: ("Slovak", "sk-SK"),
        Language.RUSSIAN: ("Russian", "ru-RU"),
        Language.NORWEGIAN: ("Norwegian", "nb-NO"),
        Language.KOREAN: ("Korean", "ko-KR"),
        Language.HUNGARIAN: ("Hungarian", "hu-HU"),
        Language.SWEDISH: ("Swedish", "sv-SE"),
        Language.INDONESIAN: ("Indonesian", "id-ID"),
        Language.JAPANESE: ("Japanese", "ja-JP"),
        Language.TURKISH: ("Turkish", "tr-TR"),
    }
    assert {language: (language.label, language.speech_locale) for language in expected} == expected


def test_script_filter_rejects_translated_list_artifacts() -> None:
    assert valid_term(Language.JAPANESE, "言葉")
    assert valid_term(Language.KOREAN, "언어")
    assert valid_term(Language.MALAYALAM, "ഭാഷ")
    assert valid_term(Language.RUSSIAN, "язык")
    assert not valid_term(Language.JAPANESE, "the")
    assert not valid_term(Language.KOREAN, "be")
    assert not valid_term(Language.MALAYALAM, "the")
    assert not valid_term(Language.RUSSIAN, "the")


def test_translated_source_can_rerank_but_cannot_add_a_candidate() -> None:
    merged = merge_rankings(
        Language.POLISH,
        ["native-one", "native-two", "native-three"],
        ["native-two", "native-one", "native-three"],
        ["translated-only", "native-two", "native-one"],
        limit=3,
    )
    assert merged[0] == "native-two"
    assert "translated-only" not in merged


def test_malayalam_uses_native_opensubtitles_gate_without_wordfreq() -> None:
    merged = merge_rankings(
        Language.MALAYALAM,
        [],
        ["ഭാഷ", "വാക്ക്"],
        ["the", "വാക്ക്", "ഭാഷ"],
        limit=2,
    )
    assert merged == ["ഭാഷ", "വാക്ക്"]
    assert "the" not in merged
