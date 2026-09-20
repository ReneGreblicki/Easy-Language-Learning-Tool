"""Generate a resumable, reviewable shared curriculum; never publish automatically.

Uses the pinned production English ranking and preserves its source attribution.
Run --pilot first. Full publication SQL requires a content-bound review manifest.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.request
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resources/frequency_data/production/words.jsonl.gz"
LANGUAGES = dict(
    re.findall(
        r"\w+\('([^']+)', '([^']+)'\)",
        (ROOT / "android_app/lib/generation/generation_settings.dart").read_text(),
    )
)


def stable_id(value: str) -> str:
    return str(UUID(hashlib.md5(value.encode(), usedforsecurity=False).hexdigest()))


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def frequency_data() -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            result.setdefault(row["language"], []).append(row)
    for rows in result.values():
        rows.sort(key=lambda row: row["rank"])
    return result


def request_rows(tasks: list[dict], language: str, model: str) -> list[dict]:
    instruction = (
        "Return one row per input id with target_word, target_sentence, and sense_in_english. "
        "All target_word and target_sentence values MUST be in " + language + ". "
        "sense_in_english MUST be English. Never copy an untranslated source headword. "
        "Use natural adult-neutral examples at the specified CEFR level. A1: simple concrete "
        "sentences; A2: everyday situations; B1: connected ideas. Target sentences must use "
        "the target headword or its grammatical inflection. Preserve concepts and IDs. "
    )
    if language == "US English":
        instruction += "Keep each input word exactly. Write one original sentence using it and identify its common intended meaning. "
    elif language == "Thai (Paiboon romanization)":
        instruction += (
            "Transliterate the supplied Thai headwords and sentences into Paiboon "
            "romanization with appropriate vowel symbols and tone marks. NO Thai characters "
            "anywhere in target_word or target_sentence. Do not translate them into English. "
        )
    else:
        instruction += (
            "Translate BOTH the source word AND its sentence. For example English "
            "'the' in German can be target_word 'die' in 'Die Katze ...'; in Spanish 'el' in "
            "'El gato ...'. When no standalone equivalent exists, use a natural contextual "
            "phrase in the target language that expresses that meaning. Do not retain the "
            "English headword as a label. Adapt grammar naturally while preserving meaning. "
        )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "target_word", "target_sentence", "sense_in_english"],
                    "properties": {
                        "id": {"type": "integer"},
                        "target_word": {"type": "string"},
                        "target_sentence": {"type": "string"},
                        "sense_in_english": {"type": "string"},
                    },
                },
            }
        },
    }
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(tasks, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "learning_rows", "strict": True, "schema": schema},
            },
            "temperature": 0.2,
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            raw = json.loads(payload["choices"][0]["message"]["content"])["rows"]
            rows = [
                {
                    "id": r["id"],
                    "word": r["target_word"],
                    "sentence": r["target_sentence"],
                    "sense": r["sense_in_english"],
                }
                for r in raw
            ]
            validate_rows(rows, tasks)
            validate_language(rows, tasks, language)
            return rows
        except (ValueError, KeyError, OSError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def validate_rows(rows: list[dict], tasks: list[dict]) -> None:
    if len(rows) != len(tasks) or {r["id"] for r in rows} != {t["id"] for t in tasks}:
        raise ValueError("Missing or duplicated concept IDs")
    for row in rows:
        if any(
            not isinstance(row.get(key), str) or not row[key].strip()
            for key in ("word", "sentence", "sense")
        ):
            raise ValueError("Empty word, sentence or sense")
        if len(row["sentence"]) > 1000 or len(row["word"]) > 160:
            raise ValueError("Unexpectedly long content")


def validate_language(rows: list[dict], tasks: list[dict], language: str) -> None:
    original = {t["id"]: t for t in tasks}
    if language == "US English":
        if any(normalize(r["word"]) != normalize(original[r["id"]]["word"]) for r in rows):
            raise ValueError("English generation changed a source word")
    elif len(rows) >= 5:
        copied = sum(normalize(r["word"]) == normalize(original[r["id"]]["word"]) for r in rows)
        if copied / len(rows) > 0.6:
            raise ValueError("Most headwords were not translated")
    for row in rows:
        for key in ("word", "sentence"):
            thai = bool(re.search(r"[\u0e00-\u0e7f]", row[key]))
            if language == "Thai (Paiboon romanization)" and thai:
                raise ValueError("Thai script found in romanization")
            if language == "Thai (Thai script)" and not thai:
                raise ValueError("Thai script missing from native translation")


def generate(output: Path, pilot: bool, languages: list[str], model: str) -> dict:
    frequencies = frequency_data()
    english = frequencies["en-US"][:1000]
    if len(english) != 1000 or len({r["rank"] for r in english}) != 1000:
        raise ValueError("Expected 1,000 English source entries")
    tasks = [
        {
            "id": r["rank"],
            "word": r["lemma"],
            "level": "A1" if r["rank"] <= 400 else "A2" if r["rank"] <= 700 else "B1",
        }
        for r in english
        if not pilot or r["rank"] in {*range(1, 11), *range(401, 411), *range(701, 711)}
    ]
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "checkpoints"
    checkpoint.mkdir(exist_ok=True)
    datasets = {}
    ordered = list(dict.fromkeys(["en-US", *languages]))
    if "th-Latn-TH" in ordered:
        if "th-Thai-TH" in ordered:
            ordered.remove("th-Thai-TH")
        ordered.insert(ordered.index("th-Latn-TH"), "th-Thai-TH")
    for code in ordered:
        if code not in LANGUAGES:
            raise ValueError(f"Unknown language: {code}")
        source_tasks = (
            tasks
            if code == "en-US"
            else datasets["th-Thai-TH" if code == "th-Latn-TH" else "en-US"]
        )
        generated = []
        for start in range(0, len(source_tasks), 20):
            batch = source_tasks[start : start + 20]
            # Changing input/model invalidates the checkpoint rather than silently reusing it.
            digest = hashlib.sha256(
                json.dumps(["prompt-v2", model, code, batch], sort_keys=True).encode()
            ).hexdigest()[:20]
            file = checkpoint / f"{code}-{digest}.json"
            rows = (
                json.loads(file.read_text())
                if file.exists()
                else request_rows(batch, LANGUAGES[code], model)
            )
            validate_rows(rows, batch)
            validate_language(rows, batch, LANGUAGES[code])
            file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            by_id = {r["id"]: r for r in rows}
            generated.extend({**by_id[t["id"]], "level": t["level"]} for t in batch)
        lookup = {normalize(r["lemma"]): r["rank"] for r in frequencies[code]}
        for row in generated:
            row["source_rank"] = lookup.get(normalize(row["word"]))
        for level in ("A1", "A2", "B1"):
            group = sorted(
                (r for r in generated if r["level"] == level),
                key=lambda r: (r["source_rank"] or 99999, r["id"]),
            )
            for rank, row in enumerate(group, 1):
                row["rank"] = rank
        datasets[code] = generated
    result = {
        "pilot": pilot,
        "model": model,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_attribution": {
            k: english[0].get(k) for k in ("source", "licence", "source_url", "source_revision")
        },
        "languages": datasets,
    }
    content = json.dumps(result, ensure_ascii=False, indent=2)
    (output / "curriculum.json").write_text(content, encoding="utf-8")
    issues = [
        f"{code} concept {r['id']}: translation not matched to ranked source"
        for code, rows in datasets.items()
        for r in rows
        if r["source_rank"] is None
    ]
    review_lines = [
        "# Curriculum pilot review",
        "",
        "Draft, not published. Check sense alignment, naturalness, target-word inclusion, CEFR suitability and script.",
        "",
    ]
    for code, rows in datasets.items():
        review_lines.extend(
            [
                "## " + LANGUAGES[code],
                "",
                "| Concept | Level | Word | Sentence | English meaning |",
                "|---|---|---|---|---|",
            ]
        )
        for row in rows:
            cells = [str(row["id"]), row["level"], row["word"], row["sentence"], row["sense"]]
            review_lines.append(
                "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"
            )
        review_lines.append("")
    review_lines.extend(["## Ranking matches to review", "", *["- " + i for i in issues]])
    review_text = "\n".join(review_lines)
    (output / "review.md").write_text(review_text, encoding="utf-8")
    if pilot and os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(review_text, encoding="utf-8")
    return result


def publication_sql(curriculum: Path, review: Path, version: int) -> str:
    content = curriculum.read_bytes()
    data, approval = json.loads(content), json.loads(review.read_text())
    if data["pilot"] or version < 1:
        raise ValueError("Only complete curricula with a positive version can be published")
    if (
        approval.get("sha256") != hashlib.sha256(content).hexdigest()
        or not approval.get("reviewer")
        or not approval.get("approved")
    ):
        raise ValueError("A review bound to this exact curriculum is required")
    if set(data["languages"]) != set(LANGUAGES):
        raise ValueError("All supported language/script options must be present")
    for rows in data["languages"].values():
        validate_rows(rows, [{"id": i} for i in range(1, 1001)])
        for level, count in [("A1", 400), ("A2", 300), ("B1", 300)]:
            group = [r for r in rows if r["level"] == level]
            if len(group) != count or sorted(r["rank"] for r in group) != list(range(1, count + 1)):
                raise ValueError("Invalid level counts or ordering")
        levels = {r["id"]: r["level"] for r in rows}
        if levels != {r["id"]: r["level"] for r in data["languages"]["en-US"]}:
            raise ValueError("Concept levels must align between languages")

    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    sql = ["begin;", "-- Reviewed shared content; personal decks are untouched."]
    for row in data["languages"]["en-US"]:
        values = [
            str(row["id"]),
            quote(row["level"]),
            quote(row["word"]),
            quote(row["sentence"]),
            quote(row["sense"]),
        ]
        sql.append(
            "insert into public.default_concepts(id,default_level,english_word,english_sentence,sense) values ("
            + ",".join(values)
            + ") on conflict(id) do update set english_word=excluded.english_word,english_sentence=excluded.english_sentence,sense=excluded.sense;"
        )
    for code, rows in data["languages"].items():
        for row in rows:
            deck = stable_id("default:" + LANGUAGES[code] + ":" + row["level"])
            card = stable_id("default-card:" + code + ":" + str(row["id"]))
            sql.append(
                f"insert into public.default_card_identity(id,deck_id,concept_id) values('{card}','{deck}',{row['id']}) on conflict(id) do nothing;"
            )
            sql.append(
                "insert into public.default_translations(card_id,content_version,word,sentence,rank,source_rank) values("
                + ",".join(
                    [
                        quote(card),
                        str(version),
                        quote(row["word"]),
                        quote(row["sentence"]),
                        str(row["rank"]),
                        str(row["source_rank"]) if row["source_rank"] else "null",
                    ]
                )
                + ");"
            )
    sql.extend([f"update public.default_decks set content_version={version};", "commit;"])
    return "\n".join(sql) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--languages", nargs="+", default=list(LANGUAGES))
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--version", type=int, default=1)
    args = parser.parse_args()
    if args.review:
        sql = publication_sql(args.output / "curriculum.json", args.review, args.version)
        (args.output / "publish.sql").write_text(sql, encoding="utf-8")
    else:
        generate(args.output, args.pilot, args.languages, args.model)


if __name__ == "__main__":
    main()
