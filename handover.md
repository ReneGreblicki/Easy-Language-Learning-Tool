# Project handover

Updated: 2026-10-10

## Repository state

- Repository: `ReneGreblicki/Easy-Language-Learning-Tool`
- Working branch: `feature/mobile-menu-privacy-analytics`
- Draft PR: https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/pull/19
- Main was merged at `3a1bc93bab34e26a021febc45af5dfa26270f081`; PR reports `mergeable: true`.
- The only conflict was the production workflow. Preserve the feature branch's recovery safeguards.
- Android development candidate: `0.6.0+12`
- Nothing in this branch has been deployed or published as default content.

## Approved product behavior

- A left drawer covers 58% of the screen and dims the remainder. It contains Home, Account
  settings, Privacy settings, Display settings, and bottom-anchored Log out.
- Default decks appear above personal decks inside **Select deck** and never consume the five
  personal-deck slots.
- Changing the learning language restores that language's prior deck; otherwise A1 is selected.
- Default card translation can change without changing card identity or progress.
- Analytics are optional and off by default. Track unique revealed cards at 10, 100, 500 and
  1,000 per account/language, first deck opened, and successful personal-deck generation.
- Analytics exclude card text, deck title, email, password, location and advertising IDs.
  Events/retry receipts expire after 90 days; opt-out deletes collected analytics identifiers.

## Default curriculum contract

- Final matrix: 1,000 stable concepts × 24 language/script options = 24,000 rows.
- Levels: IDs 1–400 A1, 401–700 A2, 701–1,000 B1.
- Select the first 1,000 valid ranked English concepts after deterministic cleaning. Invalid
  fragments, isolated letters, codes and abbreviations such as `de` are replaced by the next
  valid ranked English word. Record replacements in `concept_source` and
  `source_replacements.json`.
- Every language retains the same ID, proposition, English sense and level.
- Only ranks 1–1,000 of each target-language frequency list may supply candidates or
  `source_rank`. Never restore the old 5,000-rank matching behavior.
- Generate in ID-major blocks across languages. Thai script must precede Paiboon romanization.
- Pipeline: Google translation draft → constrained GPT post-edit → automated adjudication →
  network-free final verification. Publication requires a content-bound approval manifest.

## Generation progress and artifacts

| Item | ID/link | Result |
|---|---|---|
| Run 1 | https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/actions/runs/36122379349 | Older checkpoints; approximately 7,960 raw rows |
| Run 1 artifact | `10880027418` | Expires 2026-12-24 |
| Run 2 | https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/actions/runs/37699458069 | Failed on transient Google HTTP 503 |
| Run 2 artifact | `11518959920` | 4,780 rows; expires 2027-01-05 |
| Run 3 | https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/actions/runs/38060714209 | Started once on 2026-10-10; generation in progress at this update |

- The two artifacts were merged locally with run 2/newer files taking precedence.
- Raw union: **10,520/24,000 rows (43.8%)**.
- Rows compatible with the revised English source hashes: **5,278/24,000 (22.0%)**.
- The merge recovered 498 usable rows beyond run 2. Most older translations reference English
  sentences changed by the new review and must not be reused.
- Run 3 job `114238239134` restored cache and merged the exact artifacts successfully.
  Live merge report: 1,020 files copied, 685 collisions preserved, **10,520 raw rows**.
  Source-corpus and provider-credential gates passed before generation began.
- Run 3 has not yet produced a final artifact or a newly verified usable-row count.
  Do not dispatch another run while it is active or describe raw coverage as usable coverage.

## Resume and spending safeguards

- Production restores the newest Actions cache, downloads both exact artifact IDs, merges run 2
  before run 1, and preserves existing files on collisions.
- `tools/merge_default_deck_checkpoints.py` enforces a 10,520-raw-row floor before any paid API
  request. Missing artifacts, failed downloads or lower coverage must stop the run.
- Generator reuse remains row-level and content-hash-bound; the raw merge floor is not approval.
- Google retries HTTP 429/500/502/503/504 up to six bounded attempts.
- Google cap: 500,000 new characters per run; plan cap: 1,200,000 characters.
- OpenAI generation cap: $4.50 per run. Adjudication cap: $1.00.
- Required GitHub secrets: `OPENAI_API_KEY`, `GOOGLE_TRANSLATE_API_KEY`.
- Never print keys, place keys in URLs, commit generated secrets, or bypass the spending gates.

## Key files

- Plan and product contract: `docs/MOBILE_MENU_DEFAULT_DECKS_ANALYTICS.md`
- Production workflow: `.github/workflows/default-deck-production.yml`
- Generator: `tools/build_default_decks.py`
- English source policy: `tools/default_deck_concepts.py`
- Artifact merge: `tools/merge_default_deck_checkpoints.py`
- Automated repair: `tools/review_default_deck_curriculum.py`
- Final offline gate: `tools/default_deck_quality.py`
- Structural audit: `tools/audit_default_deck_curriculum.py`
- Mobile/default catalog: `android_app/lib/data/default_catalog.dart`
- Database migrations/tests: `supabase/` and `supabase/tests/learning_analytics.mjs`

## Last verification

- Ruff formatting and static checks passed.
- Workflow YAML parsed successfully.
- 25 focused Python tests passed.
- Real-artifact merge produced 1,679 checkpoint files, 10,520 raw rows and preserved newer files
  on all 26 filename collisions.
- The project plan records cache-miss protection, artifact merging and Google backoff behavior.
- Main-merge checks found one stale cost-control assertion (100,000 instead of the approved
  500,000-character cap). Corrected it; all eight cost-control tests pass locally.
- Dependency audit flagged multidict 6.7.1, urllib3 2.7.0 and virtualenv 21.7.4.
  Updated the lock to 6.9.1, 2.8.0 and 21.14.6 respectively, with python-discovery 1.6.2.
  Check CI on the latest commit before release; previous CI recorded 116 passing tests,
  88.04% coverage and successful learning-analytics integration checks.

Focused verification command:

```bash
uv run --no-project --with ruff ruff check \
  tools/build_default_decks.py tools/merge_default_deck_checkpoints.py \
  tests/unit/test_default_curriculum.py tests/unit/test_merge_default_deck_checkpoints.py
uv run --no-project --with 'pytest>=9,<10' python -m pytest -q \
  tests/unit/test_default_curriculum.py \
  tests/unit/test_merge_default_deck_checkpoints.py \
  tests/unit/test_default_deck_concepts.py \
  tests/unit/test_default_deck_quality.py \
  tests/unit/test_default_curriculum_audit.py
```

## Exact next actions

1. Inspect the existing Run 3 and latest PR checks; do not start a duplicate paid run.
2. Download its final artifact when available and recompute compatible coverage from its hashes.
3. Recovery floor was verified at 10,520 raw rows for Run 3. Enforce this gate on every resume;
   if recovery fails, stop instead of starting an empty run.
4. Confirm logs show compatible checkpoint reuse and bounded Google retry handling.
5. If generation exits with code 75, retain the saved artifact/cache and resume only after quota
   reset. Do not regenerate completed compatible rows.
6. When all 24,000 rows exist, allow automated adjudication and final network-free verification.
7. Inspect the quarantine/error report. Do not publish while any hard error remains.
8. Generate versioned publication SQL only from the exact approved curriculum hash.
9. Deploy migrations/content through the controlled Supabase process and verify `pg_cron`.
10. Complete physical-device account switching, offline, drawer, theme, default-deck and analytics
    consent tests before changing PR/release status.

## Do not regress

- Do not run paid generation after a cache/artifact merge failure.
- Do not publish raw model or Google output.
- Do not reuse stale source/target hashes.
- Do not change stable concept IDs or level membership without an explicit migration.
- Do not count default-deck publication/download as a user deck-generation analytics event.
- Do not delete or assign the legacy unscoped mobile cache to an account.
- The PR description now reflects automated adjudication and the fail-closed publication gates.
