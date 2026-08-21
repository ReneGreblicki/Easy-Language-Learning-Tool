# Frequency-data build and review

The application ships with a four-verb-per-language demonstration corpus. It is
deliberately capped in the interface and is not a production frequency list.

Production data follows a two-stage process:

1. `tools/build_frequency_candidates.py` reads Kaikki/Wiktionary JSONL or
   compressed JSONL entries,
   keeps verb lemmas, removes inflected-form entries, extracts available
   translations and constructions, deduplicates lemmas, and ranks candidates
   with `wordfreq`.
2. A language reviewer completes missing translations, removes unsuitable or
   regional entries, confirms European Spanish and Portuguese usage, sets
   `review_status` to `approved`, and records `reviewer`, `reviewed_at`, and
   `review_notes`. `tools/build_frequency_data.py` then creates the runtime
   JSONL file and `tools/check_release_data.py` enforces the release gate.

Candidate extraction example:

```powershell
uv sync --extra data-build
uv run python tools\build_frequency_candidates.py `
  --input en-US=C:\data\kaikki-English.jsonl `
  --input es-ES=C:\data\kaikki-Spanish.jsonl `
  --input de-DE=C:\data\kaikki-German.jsonl `
  --input pt-PT=C:\data\kaikki-Portuguese.jsonl `
  --input fr-FR=C:\data\kaikki-French.jsonl `
  --source-revision enwiktionary-2026-08-05 `
  --output resources\frequency_data\review\verbs.tsv
```

After review:

```powershell
uv run python tools\build_frequency_data.py `
  resources\frequency_data\review\verbs.tsv `
  resources\frequency_data\production\verbs.jsonl
uv run python tools\check_release_data.py `
  resources\frequency_data\production\verbs.jsonl --minimum 4000
```

Run `uv run python tools\audit_frequency_review.py
resources\frequency_data\review\verbs.tsv` throughout review to report candidate,
translation, approval, flag, and duplicate counts for every language.

The release gate requires at least 4,000 unique, continuously ranked,
human-approved verbs per language. Every record must contain translations into
all four other supported languages and complete source, licence, revision, and
review metadata.
