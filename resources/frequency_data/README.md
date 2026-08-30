# Frequency-data build and automated validation

The development build ships with four multi-POS demonstration words per language. A production build requires exactly 5,000 ranked words for each of US English, European Spanish, German, European Portuguese, French, and Italian.

Canonical ranking uses `wordfreq.top_n_list`. Kaikki/Wiktionary supplies lemma, part of speech, forms, and available translations. The supplied public lists are comparison sources only unless their licences explicitly permit redistribution.

```powershell
uv sync --extra data-build
uv run python tools\build_frequency_candidates.py `
  --input en-US=C:\data\kaikki-English.jsonl.gz `
  --input es-ES=C:\data\kaikki-Spanish.jsonl.gz `
  --input de-DE=C:\data\kaikki-German.jsonl.gz `
  --input pt-PT=C:\data\kaikki-Portuguese.jsonl.gz `
  --input fr-FR=C:\data\kaikki-French.jsonl.gz `
  --input it-IT=C:\data\kaikki-Italian.jsonl.gz `
  --source-revision 2026-08-20 `
  --limit 5000 `
  --output resources\frequency_data\build\words.tsv
```

Dictionary translations are often incomplete. An automated enrichment job must fill missing language cells, run same-language leakage and back-translation checks, and set `validation_status=automated` only on passing rows. Then compile and gate:

```powershell
uv run python tools\build_frequency_data.py `
  resources\frequency_data\build\words.tsv `
  resources\frequency_data\production\words.jsonl.gz
uv run python tools\check_release_data.py `
  resources\frequency_data\production\words.jsonl.gz --minimum 5000
```

The gate verifies six-language coverage, contiguous ranks, unique normalized lemmas, all five translations, part of speech, attribution, revision, and automated status. Build artifacts must also record input hashes, tool versions, and a cross-source comparison report so the corpus is reproducible.
