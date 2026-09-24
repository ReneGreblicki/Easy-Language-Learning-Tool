"""Network-free verification and release gating for generated default decks.

This module intentionally has no HTTP or model-provider dependency. It validates every
row against the pinned frequency corpus and optional independent back-translations, emits
inspectable findings, and creates a content-bound approval manifest only when every hard
gate passes.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "resources/frequency_data/production/words.jsonl.gz"

EXPECTED_SCRIPTS = {
    "zh-CN": re.compile(r"[\u3400-\u9fff]"),
    "ml-IN": re.compile(r"[\u0d00-\u0d7f]"),
    "ru-RU": re.compile(r"[\u0400-\u04ff]"),
    "ko-KR": re.compile(r"[\uac00-\ud7af]"),
    "ja-JP": re.compile(r"[\u3040-\u30ff\u3400-\u9fff]"),
    "th-Thai-TH": re.compile(r"[\u0e00-\u0e7f]"),
}
THAI = re.compile(r"[\u0e00-\u0e7f]")
LATIN = re.compile(r"[A-Za-z]")
TONE_MARKS = {"\u0300", "\u0301", "\u0302", "\u030c"}
PLACEHOLDERS = {
    "-",
    "—",
    "n/a",
    "na",
    "none",
    "unknown",
    "no equivalent",
    "no direct equivalent",
    "（无对应词）",
    "无对应词",
    "해당 없음",
    "없음",
    "該当なし",
}
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "she",
    "that",
    "the",
    "their",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "will",
    "with",
    "you",
    "your",
}


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def english_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z]+(?:'[a-z]+)?", normalized(value))
        if len(token) > 1 and token not in ENGLISH_STOPWORDS
    }


def content_similarity(left: str, right: str) -> float:
    """Conservative lexical agreement for independently back-translated English."""
    left_tokens, right_tokens = english_tokens(left), english_tokens(right)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


@dataclass(frozen=True)
class Finding:
    language: str
    concept_id: int | None
    severity: str
    code: str
    message: str
    repairable: bool = False


def load_corpus(path: Path) -> tuple[dict[str, dict[str, dict]], str]:
    indexes: dict[str, dict[str, dict]] = defaultdict(dict)
    raw = path.read_bytes()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            indexes[row["language"]][normalized(row["lemma"])] = row
    return dict(indexes), hashlib.sha256(raw).hexdigest()


def load_backtranslations(path: Path | None) -> dict[tuple[str, int], dict]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"] if isinstance(data, dict) else data
    result = {}
    for row in rows:
        key = (row["language"], int(row["id"]))
        if key in result:
            raise ValueError(f"Duplicate independent translation: {key}")
        result[key] = row
    return result


def expected_level_counts(pilot: bool) -> dict[str, int]:
    return {"A1": 10, "A2": 10, "B1": 10} if pilot else {"A1": 400, "A2": 300, "B1": 300}


def verify(
    curriculum_path: Path,
    corpus_path: Path = DEFAULT_CORPUS,
    backtranslations_path: Path | None = None,
    require_independent: bool = True,
) -> dict:
    curriculum_bytes = curriculum_path.read_bytes()
    curriculum = json.loads(curriculum_bytes)
    corpus, corpus_sha = load_corpus(corpus_path)
    independent = load_backtranslations(backtranslations_path)
    findings: list[Finding] = []
    languages: dict[str, list[dict]] = curriculum.get("languages", {})
    english_rows = {row["id"]: row for row in languages.get("en-US", [])}
    expected_ids = set(english_rows)
    level_counts = expected_level_counts(bool(curriculum.get("pilot")))
    row_status: dict[str, dict[int, str]] = defaultdict(dict)

    if curriculum.get("source_sha256") != corpus_sha:
        findings.append(
            Finding(
                "*",
                None,
                "error",
                "source_hash_mismatch",
                "Curriculum was not generated from the pinned corpus.",
            )
        )
    if set(languages) != set(corpus):
        missing, extra = sorted(set(corpus) - set(languages)), sorted(set(languages) - set(corpus))
        findings.append(
            Finding(
                "*", None, "error", "language_set_mismatch", f"Missing={missing}; extra={extra}."
            )
        )

    independent_expected = 0
    independent_present = 0
    frequency_matches = 0
    absent_headwords = 0
    for code, rows in languages.items():
        ids = [int(row.get("id", -1)) for row in rows]
        if len(ids) != len(set(ids)):
            findings.append(
                Finding(code, None, "error", "duplicate_ids", "Concept IDs are duplicated.")
            )
        if set(ids) != expected_ids:
            findings.append(
                Finding(
                    code, None, "error", "concept_set_mismatch", "Concept IDs differ from English."
                )
            )
        counts = Counter(row.get("level") for row in rows)
        if dict(counts) != level_counts:
            findings.append(
                Finding(
                    code,
                    None,
                    "error",
                    "level_counts",
                    f"Observed {dict(counts)}; expected {level_counts}.",
                )
            )
        normalized_sentences = [normalized(str(row.get("sentence", ""))) for row in rows]
        if len(normalized_sentences) != len(set(normalized_sentences)):
            findings.append(
                Finding(code, None, "error", "duplicate_sentences", "Sentences are duplicated.")
            )

        for row in rows:
            concept_id = int(row.get("id", -1))
            word = str(row.get("word", "")).strip()
            sentence = str(row.get("sentence", "")).strip()
            sense = str(row.get("sense", "")).strip()
            row_errors = 0

            def add(
                severity: str,
                issue_code: str,
                message: str,
                repairable: bool = False,
                *,
                language: str = code,
                row_id: int = concept_id,
            ) -> None:
                nonlocal row_errors
                findings.append(
                    Finding(language, row_id, severity, issue_code, message, repairable)
                )
                row_errors += severity == "error"

            if not word or not sentence or not sense:
                add("error", "missing_content", "Word, sentence, or sense is empty.", True)
            if normalized(word) in PLACEHOLDERS:
                add("error", "placeholder", f"Unusable headword placeholder: {word!r}.", True)
            source = english_rows.get(concept_id)
            if source and code != "en-US" and normalized(sense) != normalized(source["sense"]):
                add("error", "sense_drift", "English sense differs from the source concept.", True)
            if source and code == "en-US" and normalized(word) != normalized(source["word"]):
                add("error", "english_word_changed", "English source word was changed.", True)

            script = EXPECTED_SCRIPTS.get(code)
            if script and (not script.search(word) or not script.search(sentence)):
                add(
                    "error",
                    "missing_script",
                    "Expected writing system is missing from word or sentence.",
                    True,
                )
            if code == "th-Latn-TH":
                combined = word + " " + sentence
                if THAI.search(combined):
                    add(
                        "error",
                        "mixed_thai_script",
                        "Thai script appears in Paiboon romanization.",
                        True,
                    )
                decomposed = unicodedata.normalize("NFD", combined)
                if not any(mark in decomposed for mark in TONE_MARKS):
                    add(
                        "error",
                        "missing_tone_marks",
                        "Paiboon romanization has no tone marks.",
                        True,
                    )

            corpus_row = corpus.get(code, {}).get(normalized(word))
            if corpus_row:
                frequency_matches += 1
                stored_rank = row.get("source_rank")
                if stored_rank != corpus_row["rank"]:
                    add(
                        "error",
                        "incorrect_source_rank",
                        f"Stored source_rank={stored_rank}; corpus rank={corpus_row['rank']}.",
                        False,
                    )
            else:
                add(
                    "warning",
                    "headword_not_in_top_5000",
                    "Headword is not an exact match in the ranked 5,000-word corpus.",
                    True,
                )

            if code != "en-US" and normalized(word) not in normalized(sentence):
                absent_headwords += 1
                add(
                    "warning",
                    "headword_not_verbatim",
                    "Headword is not verbatim in the sentence; inflection may be valid.",
                    True,
                )
            if (
                code != "en-US"
                and source
                and len(word) > 2
                and normalized(word) == normalized(source["word"])
            ):
                severity = "error" if normalized(word) not in corpus.get(code, {}) else "warning"
                add(
                    severity,
                    "possible_untranslated_word",
                    "Target headword equals the English source.",
                    True,
                )

            source_numbers = (
                set(re.findall(r"\d+(?:[.,]\d+)?", source["sentence"])) if source else set()
            )
            target_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", sentence))
            if source_numbers != target_numbers:
                add(
                    "error",
                    "number_drift",
                    f"Source numbers {sorted(source_numbers)} differ from target {sorted(target_numbers)}.",
                    True,
                )

            if code != "en-US":
                independent_expected += 1
                evidence = independent.get((code, concept_id))
                if evidence:
                    independent_present += 1
                    if (
                        evidence.get("source_sha256")
                        and evidence["source_sha256"]
                        != hashlib.sha256((word + "\n" + sentence).encode()).hexdigest()
                    ):
                        add(
                            "error",
                            "stale_independent_review",
                            "Independent translation does not match the reviewed row.",
                            False,
                        )
                    else:
                        similarity = (
                            content_similarity(
                                source["sentence"], evidence.get("backtranslated_sentence", "")
                            )
                            if source
                            else 0.0
                        )
                        expected_word_tokens = english_tokens(
                            (source["word"] + " " + source["sense"]) if source else ""
                        )
                        reviewed_word_tokens = english_tokens(
                            evidence.get("backtranslated_word", "")
                        )
                        if expected_word_tokens and not (
                            expected_word_tokens & reviewed_word_tokens
                        ):
                            add(
                                "error",
                                "backtranslated_word_conflict",
                                "Independent word translation does not overlap the source word or sense.",
                                True,
                            )
                        if similarity < 0.08:
                            add(
                                "error",
                                "backtranslation_conflict",
                                f"Independent back-translation has near-zero lexical agreement ({similarity:.3f}).",
                                True,
                            )
                        elif similarity < 0.18:
                            add(
                                "warning",
                                "backtranslation_low_agreement",
                                f"Independent back-translation has low lexical agreement ({similarity:.3f}).",
                                True,
                            )
                elif require_independent:
                    add(
                        "error",
                        "independent_review_missing",
                        "No independent back-translation evidence exists for this row.",
                        False,
                    )

            row_status[code][concept_id] = "quarantined" if row_errors else "accepted"

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    total_rows = sum(len(rows) for rows in languages.values())
    accepted_rows = sum(
        status == "accepted" for values in row_status.values() for status in values.values()
    )
    by_code = Counter(finding.code for finding in findings)
    report = {
        "schema_version": 1,
        "verifier": "offline-default-deck-verifier-v1",
        "network_access": False,
        "curriculum_sha256": hashlib.sha256(curriculum_bytes).hexdigest(),
        "corpus_sha256": corpus_sha,
        "approved": not errors and independent_present == independent_expected,
        "summary": {
            "languages": len(languages),
            "rows": total_rows,
            "accepted_rows": accepted_rows,
            "quarantined_rows": total_rows - accepted_rows,
            "errors": len(errors),
            "warnings": len(warnings),
            "frequency_exact_matches": frequency_matches,
            "headwords_not_verbatim": absent_headwords,
            "independent_reviews_present": independent_present,
            "independent_reviews_expected": independent_expected,
        },
        "finding_counts": dict(sorted(by_code.items())),
        "findings": [asdict(finding) for finding in findings],
        "row_status": {
            code: {str(key): value for key, value in statuses.items()}
            for code, statuses in row_status.items()
        },
    }
    return report


def write_outputs(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "offline_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = report["summary"]
    lines = [
        "# Offline default-deck verification",
        "",
        f"**Decision:** {'APPROVED' if report['approved'] else 'QUARANTINED'}",
        "",
        "| Measure | Value |",
        "|---|---:|",
        *[f"| {key.replace('_', ' ').title()} | {value} |" for key, value in summary.items()],
        "",
        "## Findings",
        "",
        "| Code | Count |",
        "|---|---:|",
        *[f"| {key} | {value} |" for key, value in report["finding_counts"].items()],
    ]
    (output / "offline_verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if report["approved"]:
        manifest = {
            "approved": True,
            "reviewer": report["verifier"],
            "sha256": report["curriculum_sha256"],
            "corpus_sha256": report["corpus_sha256"],
            "evidence": "offline_verification.json",
        }
        (output / "review.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curriculum", type=Path)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--backtranslations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-missing-independent", action="store_true")
    args = parser.parse_args()
    report = verify(
        args.curriculum, args.corpus, args.backtranslations, not args.allow_missing_independent
    )
    write_outputs(report, args.output)
    print(json.dumps(report["summary"], indent=2))
    if not report["approved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
