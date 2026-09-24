import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/default_deck_quality.py"
spec = importlib.util.spec_from_file_location("default_deck_quality", SCRIPT)
assert spec and spec.loader
quality = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = quality
spec.loader.exec_module(quality)


def write_corpus(path: Path, languages: list[str]) -> str:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for code in languages:
            for rank in range(1, 31):
                lemma = f"word{rank}" if code == "en-US" else f"단어{rank}"
                stream.write(
                    json.dumps(
                        {
                            "language": code,
                            "rank": rank,
                            "lemma": lemma,
                            "forms": [lemma],
                        }
                    )
                    + "\n"
                )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(code: str) -> list[dict]:
    result = []
    for concept_id in range(1, 31):
        level = "A1" if concept_id <= 10 else "A2" if concept_id <= 20 else "B1"
        word = f"word{concept_id}" if code == "en-US" else f"단어{concept_id}"
        result.append(
            {
                "id": concept_id,
                "level": level,
                "word": word,
                "sentence": f"{word} sentence {concept_id}.",
                "sense": f"sense {concept_id}",
                "source_rank": concept_id,
            }
        )
    return result


def test_clean_english_pilot_is_approved_without_network(tmp_path):
    corpus = tmp_path / "corpus.jsonl.gz"
    source_sha = write_corpus(corpus, ["en-US"])
    curriculum = tmp_path / "curriculum.json"
    curriculum.write_text(
        json.dumps(
            {
                "pilot": True,
                "source_sha256": source_sha,
                "languages": {"en-US": rows("en-US")},
            }
        )
    )
    report = quality.verify(curriculum, corpus)
    assert report["approved"] is True
    assert report["summary"]["accepted_rows"] == 30
    assert report["network_access"] is False


def test_placeholder_and_missing_script_are_quarantined(tmp_path):
    corpus = tmp_path / "corpus.jsonl.gz"
    source_sha = write_corpus(corpus, ["en-US", "ko-KR"])
    korean = rows("ko-KR")
    korean[4]["word"] = "-"
    curriculum = tmp_path / "curriculum.json"
    curriculum.write_text(
        json.dumps(
            {
                "pilot": True,
                "source_sha256": source_sha,
                "languages": {"en-US": rows("en-US"), "ko-KR": korean},
            }
        )
    )
    report = quality.verify(curriculum, corpus, require_independent=False)
    assert report["approved"] is False
    assert report["row_status"]["ko-KR"]["5"] == "quarantined"
    assert report["finding_counts"]["placeholder"] == 1
    assert report["finding_counts"]["missing_script"] == 1


def test_backtranslation_checks_word_sense_and_sentence():
    assert (
        quality.content_similarity("The cat sleeps on the sofa.", "A cat is sleeping on a sofa.")
        > 0.4
    )
    assert quality.content_similarity("The cat sleeps.", "We bought a car.") == 0


def test_content_bound_hybrid_evidence_is_accepted(tmp_path):
    corpus = tmp_path / "corpus.jsonl.gz"
    source_sha = write_corpus(corpus, ["en-US", "ko-KR"])
    english = rows("en-US")
    korean = rows("ko-KR")
    curriculum = tmp_path / "curriculum.json"
    curriculum.write_text(
        json.dumps(
            {
                "pilot": True,
                "source_sha256": source_sha,
                "languages": {"en-US": english, "ko-KR": korean},
            }
        )
    )
    evidence = tmp_path / "hybrid.json"
    evidence.write_text(
        json.dumps(
            {
                "pipeline": "google-draft-gpt-post-edit-v1",
                "rows": [
                    {
                        "language": "ko-KR",
                        "id": target["id"],
                        "draft_provider": "google-cloud-translation-v2",
                        "editor_model": "gpt-5.6-luna",
                        "google_draft_sentence": target["sentence"],
                        "source_sha256": hashlib.sha256(
                            (
                                source["word"] + "\n" + source["sentence"] + "\n" + source["sense"]
                            ).encode()
                        ).hexdigest(),
                        "target_sha256": hashlib.sha256(
                            (target["word"] + "\n" + target["sentence"]).encode()
                        ).hexdigest(),
                    }
                    for source, target in zip(english, korean, strict=True)
                ],
            }
        )
    )
    report = quality.verify(curriculum, corpus, hybrid_evidence_path=evidence)
    assert report["approved"] is True
    assert report["summary"]["independent_reviews_present"] == 30

    payload = json.loads(evidence.read_text())
    payload["rows"][0]["target_sha256"] = "stale"
    evidence.write_text(json.dumps(payload))
    report = quality.verify(curriculum, corpus, hybrid_evidence_path=evidence)
    assert report["approved"] is False
    assert report["finding_counts"]["stale_hybrid_evidence"] == 1
