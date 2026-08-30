# Easy Language Learning Tool

## Development Workflow and Test Plan

Version: 2.1 (release hardening)

Target: Windows 10/11 x64 desktop app and regular installer

Interface language: US English

Supported learning/translation languages: US English, European Spanish, German, European Portuguese, French, Italian

## 1. Locked product rules

### Ranked-word generation

- The app uses the 5,000 most common study words in each supported language, across all parts of speech.
- The app—not the AI model—chooses ranked words deterministically.
- Canonical ranking comes from `wordfreq`; Kaikki/Wiktionary supplies lemma, part of speech, grammatical forms, and available translations.
- `frequencylist.com`, the supplied Spanish/French/Portuguese lists, OCR vocabulary PDF, and `top10000words.com` are automated comparison sources, not silently redistributed canonical data.
- Records carry rank, lemma, part of speech, forms, translations, confidence, source, licence, URL, revision, and automated-validation status.
- Standard formal national usage is preferred; slang, obsolete, vulgar, malformed, foreign-language leakage, and duplicates are filtered.

### Row limits and extra forms

- Final output is always limited to 5,000 rows.
- `final_rows = base_words × (1 + extra_forms)` where extra forms are 0–4.
- `maximum_base_words = floor(5,000 ÷ (1 + extra_forms))`.
- Therefore the maxima for 0, 1, 2, 3, and 4 extra forms are 5,000; 2,500; 1,666; 1,250; and 1,000 base words respectively.
- The Sentence Creation page explains this formula above the controls and updates the base-word maximum immediately.
- Extra forms are part-of-speech aware: verb inflection; noun number/case; adjective/determiner/pronoun agreement, case, or comparison; and other supported changes.
- If a word is invariant or has fewer distinct forms than requested, an extra row may retain the surface form but must use a distinct, complete context and be labelled `invariant-context-N`.

### AI providers and cost

Providers: OpenAI, Anthropic, Google Gemini, DeepSeek, Ollama, and custom OpenAI-compatible endpoints. Users provide their own API key where required and choose a discovered model. Optional key persistence uses Windows Credential Manager only. With no cloud key, **Show more** explains Ollama installation and local-model setup. Costs are estimates for 1,000–5,000 rows plus the current configuration; provider billing remains authoritative.

### CEFR and composition

- CEFR order is `A1 → A2 → B1 → B2 → C1 → C2`; gradual ranges must be contiguous.
- Maximum sentence lengths are 5, 8, 11, 14, 17, and 20 words respectively.
- CEFR controls vocabulary, grammar, and length; out-of-level vocabulary is minimized.
- Percentages total exactly 100%; largest-remainder allocation is deterministic; output is ordered from lower to higher CEFR.
- Question percentage means questions versus declarative statements. Both yes/no and open questions are allowed; no answer field is generated.
- Every sentence contains the selected word/form, stands alone, makes sense, and uses formal standard language.
- Translations prioritize accuracy and direct wording without losing meaning.

The sentence-subject scale is applied across every final row, including extra-form
rows. Value 0 keeps all rows neutral or impersonal. Values 1–4 assign exactly
20%, 40%, 60%, or 80% of rows to personal subject patterns, with the remaining
rows neutral or impersonal. Value 5 changes the subject pattern on every
consecutive row, includes neutral or impersonal structures in the rotation, and
does not repeat the immediately preceding pattern. Planning is deterministic for
the same settings, seed, and corpus.

### Workbook, TTS, history, and design

The canonical `.xlsx` `Sentences` sheet has exactly:

1. Foreign-language word
2. Word translation
3. Foreign-language sentence
4. Sentence translation

`Metadata` includes CEFR, frequency rank, grammatical person, word form/variant, sentence type, timestamp, model/provider, validation, seed, usage, cost, and generation settings. CSV export is optional. Older four-column verb workbooks remain import-compatible.

TTS speaks all four cells in order, using the foreign voice for columns 1 and 3 and translation voice for columns 2 and 4. It produces one MP3 with voice, speed, pitch, volume, four 1–10 second pauses, two-row preview, pause/resume/cancel, partial export, and checksum-safe continuation.

History retains 20 app-owned spreadsheets and 20 audio files in application data. Rename/delete never affect external exports; delete and retention use the Recycle Bin. Regeneration preserves the original.

The PySide6 app launches centered at 50% of the available screen, supports resizing/maximizing, light/dark Power BI-inspired palettes, and the Sentence Creation, TTS, and History tabs. Branding remains a world map with letters emerging from it.

## 2. Corpus workflow

1. Pin the `wordfreq` release and Kaikki dump dates/checksums.
2. Produce the top candidate order for each of the six languages with `wordfreq.top_n_list`.
3. Join candidates to Kaikki entries; reject form-only entries and excluded usage tags.
4. Normalize Unicode and spacing, classify part of speech, collect forms, and deduplicate by normalized lemma so base words do not repeat.
5. Retain dictionary translations, POS, and forms where available; otherwise mark POS unknown, retain the base form, and have the selected generation provider supply the translation/form in context.
6. Automatically validate generated translation presence, same-language leakage, rank continuity, form use, source/licence metadata, and locale rules.
7. Compare overlap and rank displacement against the supplied secondary sources; record but do not automatically copy restricted material.
8. Compile only rows marked `automated` into `resources/frequency_data/production/words.jsonl`.
9. Require exactly 5,000 contiguous ranks per language before a production release.
10. Emit an audit summary, source manifest, checksums, and attribution notices.

This workflow does not require a human linguistic approval gate. Automated tests still report uncertainty rather than claiming that ranked corpora or machine translations are error-free.

## 3. Creation phases and gates

### Phase 0 — Foundation

PySide6 shell, config/logging, SQLite, lock file, CI, security, installer scaffold, and licence inventory. Gate: clean environment installs; app launches at 50%; lint/type/unit/dependency checks pass; no secrets are committed.

### Phase 1 — Six-language word corpus

All-word models, wordfreq/Kaikki build tools, comparison reports, Italian support, form policy, source notices, and automated release gate. Gate: 30,000 production records; 5,000 per language; contiguous ranks; unique words; POS/form fallback; source/licence fields; reproducible checksum.

### Phase 2 — Deterministic planning

Dynamic row limit, CEFR allocation, question/statement allocation, pronoun schedule, and POS-aware form expansion. Gate: identical settings/seed/corpus produce identical plans; all counts reconcile; no plan exceeds 5,000.

### Phase 3 — Providers and generation

Provider adapters, credential protection, model discovery, estimates, structured prompting, checkpoint/resume, row validation/retry, XLSX/CSV. Gate: provider contract tests pass; accepted rows contain their assigned word/form and meet schema, CEFR length, sentence-type, and translation checks.

### Phase 4 — TTS and recovery

Edge voice discovery including Italian, preview, MP3 assembly, four pauses, controls, partial output, manifest, resume. Gate: order/language/pause/codec/checksum tests pass; interruption neither skips nor duplicates rows.

### Phase 5 — History and UI

Safe local history, 20+20 retention, recycle-bin actions, three tabs, themes, accessibility, and responsive workers. Gate: path-safety and UI-state tests pass; external files are never mutated.

### Phase 6 — Packaging and release

Nuitka bundle, FFmpeg, Inno Setup, README, notices, release notes, checksum, provenance, Windows acceptance, Defender scan, and optional Authenticode signing. Gate: CI silently installs into a Unicode path, launches, upgrades/repairs, verifies bundled resources, uninstalls, and preserves user data; clean Windows 10/11 client installs require no separate Python/Qt/FFmpeg downloads; Ollama remains optional.

## 4. Test measures during development

| Layer | Mandatory measures | Run |
|---|---|---|
| Unit | row-limit matrix, allocation, schedules, normalization, POS/form rules, validators | Every commit |
| Corpus | count/rank/key/Unicode/POS/forms/translations/licences/checksums/cross-source report | Corpus change and release |
| Contract | all provider adapters, error mapping, usage, cancellation, secret redaction | Every pull request |
| Integration | generation checkpoint, XLSX/CSV round-trip, SQLite/history, mocked Edge/FFmpeg | Every pull request |
| UI | dynamic base maximum, explanation, Italian, tabs/themes, valid-button states, workers | Every pull request |
| End-to-end | controlled multi-POS generation and TTS resume | Nightly and release |
| Packaging | executable, installer, upgrade/uninstall, bundled files/notices | Release candidate |
| Security/performance | dependency audit, malformed files, path escape, 5,000-row timing/memory | Pull request/release |

### Required row-limit cases

- `5,000 × 1 = 5,000`, `2,500 × 2 = 5,000`, `1,666 × 3 = 4,998`, `1,250 × 4 = 5,000`, and `1,000 × 5 = 5,000` pass.
- The next base value in each mode fails when it would exceed 5,000.
- Changing the extra-form dropdown clamps the UI maximum immediately without silently changing the selected extra-form value.
- Imported workbooks above 5,000 rows are rejected clearly.

### Required corpus/form cases

- All six languages contain 5,000 ordered entries; dictionary evidence is retained and missing translations/forms are generated and validated in context.
- Noun, verb, adjective, adverb, pronoun/determiner, conjunction/preposition, and invariant examples are present in fixtures.
- Extra forms belong to the same lemma and POS; distinct available forms are not repeated before exhaustion.
- Invariant fallback generates a distinct coherent sentence and records `invariant-context-N`.
- Locale checks prefer en-US, es-ES, and pt-PT national standards.
- Automated comparison flags material divergence from secondary ranked sources without importing unlicensed text.

### Sentence and workbook cases

- Every accepted sentence includes `used_word_form`; the declared form appears in the foreign sentence.
- Question/statement and CEFR distributions reconcile exactly; CEFR blocks ascend.
- UTF-8 accents and punctuation survive XLSX/CSV round trips.
- New word headers are exact; previous verb headers import for backward compatibility.
- Workbook XML contains no incompatible table object; Excel opens without repair.

### TTS/history/installer cases

- Six-language Edge voice filtering, four-cell order, two-row preview, configured pauses, audio controls, cancellation, failure, partial playback, and resume are tested.
- Retention is independent per file type; path traversal, symlink/junction escape, collision, and rollback cases are covered.
- CI tests silent install into a path with spaces/Unicode, launch, in-place upgrade/repair, uninstall, bundled FFmpeg/resources, and preserved app-owned data.
- Final clean Windows 10 and Windows 11 client machines verify interactive install, shortcuts, SmartScreen/Defender behaviour, upgrade, repair, uninstall, and preserved exports.

Performance targets: cold launch ≤5 seconds; local UI response ≤200 ms; 5,000-row import ≤3 seconds; peak workbook handling ≤750 MB; 40-item history load ≤1 second. Network and FFmpeg work never block the UI thread.

## 5. CI and release acceptance

- `quality.yml`: Ruff format/lint, mypy, secret scan, dependency and licence audit.
- `tests.yml`: unit, contract, integration, headless UI, corpus fixtures, coverage.
- `windows-build.yml`: executable, optional Authenticode signing, installer, launch smoke, silent install/upgrade/uninstall acceptance, layout/notices, provenance, and SHA-256 artifact.
- `release.yml`: repeat required checks and publish installer, README, notices, release notes, checksum, and provenance after an approved tag.

Release checklist:

Production 1.0.0 status: Quality, Tests, corpus validation, Windows packaging,
silent install, launch, upgrade/repair, uninstall, bundled-resource validation,
user-data preservation, provenance, checksum, and clean Windows 10/11
client-machine acceptance pass. Tag-driven publishing repeats these gates and
creates the GitHub release. Pull-request artifacts remain intentionally unsigned;
production tags use Authenticode when the protected publisher certificate secrets
are configured.

- [x] Six languages and 30,000 production word records pass the corpus gate.
- [x] Every configuration obeys the dynamic 5,000-row cap.
- [x] POS-aware and invariant extra-form paths pass.
- [x] OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom adapters pass contracts.
- [x] Word workbook, legacy import, TTS recovery, and history safety pass.
- [x] App launches centered at 50% with usable light/dark themes.
- [x] Clean Windows installer needs no separate Python, Qt, or FFmpeg download.
- [x] Production signing and provenance automation is configured.
- [x] README, notices, source manifest, release notes, and checksum are included.
- [x] No critical/high defect or required-check failure remains.

## 6. Definition of done

A change is done only when its acceptance criteria, automated tests, error/cancellation/recovery paths, user text, README, source/licence notices, and applicable packaged-Windows verification are complete. `main` remains releasable; feature branches use pull requests; production data changes include a reproducible source manifest and corpus audit.
