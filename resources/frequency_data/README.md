# Frequency-data build and automated validation

The development build ships with four multi-POS demonstration words per language.
A production build requires exactly 5,000 ranked words for each of 24 language/script
options: the original six languages, both Thai representations, and Polish, Dutch,
Danish, Croatian, Vietnamese, Simplified Chinese, Malayalam, Slovak, Russian,
Norwegian Bokmal, Korean, Hungarian, Swedish, Indonesian, Japanese, and Turkish.

Canonical ranking uses `wordfreq.top_n_list` for the original six languages.
Kaikki/Wiktionary supplies lemma, part of speech, forms, and available translations.
The supplied public lists are comparison sources only unless their licences
explicitly permit redistribution.

The 16-language expansion uses weighted rank agreement between `wordfreq`, the
CC BY-SA OpenSubtitles 2018 lists referenced by Wiktionary's frequency-list index,
and `frekwencja/most-common-words-multilingual`, which derives its data from the
free `wordfrequency.info` English sample and machine translation. The frekwencja
signal has meaningful reranking weight, but cannot introduce a word unless a
native-language corpus also contains it. Script checks remove translated-list
artifacts. Malayalam, which is absent from wordfreq 3.1.1, uses native OpenSubtitles
as its candidate gate and frekwencja only as agreement evidence. Existing sources
remain unchanged. `MULTISOURCE_MANIFEST.json` pins the policy and revisions.

Thai uses the CC BY-SA 4.0 OpenSubtitles 2018 conversational ranking, completed
with the CC0 Phupha 2026 Common Crawl frequency dataset. Kaikki/Wiktionary filters
the candidates to dictionary words, supplies part of speech, and provides Paiboon
romanization. `THAI_SOURCE_MANIFEST.json` pins every input and checksum. Lenguia,
1000MostCommonWords.com, and the all-rights-reserved Scribd 4,000-word document
are not copied into the application.

```powershell
uv sync --extra data-build
uv run python tools\build_multisource_frequency_data.py `
  --frequencywords-root C:\data\FrequencyWords `
  --frekwencja-root C:\data\most-common-words-multilingual `
  --base resources\frequency_data\production\words.jsonl.gz `
  --output resources\frequency_data\production\words.jsonl.gz

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

The gate verifies all 24 language/script options, contiguous ranks, unique
normalized lemmas, part of speech, attribution, revision, and automated status.
Build artifacts also record input hashes, tool versions, and cross-source evidence
so the corpus is reproducible.
