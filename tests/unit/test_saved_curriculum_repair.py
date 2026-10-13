import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import review_default_deck_curriculum as review


def test_replacement_english_rank_survives_target_limit(tmp_path):
    corpus = tmp_path / "corpus.jsonl.gz"
    with gzip.open(corpus, "wt") as stream:
        for code in ("en-US", "pl-PL"):
            stream.write(
                json.dumps({"language": code, "lemma": "replacement", "rank": 1012}) + "\n"
            )
    curriculum = {
        "languages": {
            "en-US": [{"word": "replacement", "source_rank": None}],
            "pl-PL": [{"word": "replacement", "source_rank": 1012}],
        }
    }
    assert review.reconcile_source_ranks(curriculum, corpus) == 2
    assert curriculum["languages"]["en-US"][0]["source_rank"] == 1012
    assert curriculum["languages"]["pl-PL"][0]["source_rank"] is None
