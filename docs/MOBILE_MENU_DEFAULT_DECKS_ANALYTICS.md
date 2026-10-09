# Mobile menu, default decks and learning milestones

Status: implementation PR; default content and physical-device release verification pending.

## Accepted behavior

- Drawer at left, 58% of screen width, dimmed remainder. Home, Account settings,
  Privacy settings, Display settings; Log out anchored at bottom.
- Default decks appear inside **Select deck**, above My decks, not on the landing page.
- Select the remembered deck for each learning language; otherwise select its A1 default.
- Three shared decks per language/script option: A1 400, A2 300, B1 300.
  Separate catalog tables mean they never consume the five personal-deck slots.
- Default translations can be changed in Select deck. US English is the initial translation;
  English learning defaults to European Spanish. Card IDs do not depend on translation or rank.
- Downloads can be removed without deleting default content or progress.
- Accounts require sign-in when switching and use separate SQLite/audio directories.
  Previously unscoped local data is preserved, but deliberately not assigned to any account.
  Existing users must re-download their cloud decks. Unsynced legacy progress is not migrated.

## Analytics contract

Optional and off by default. A unique card is counted when the answer is revealed in
flashcard mode. Merely opening a list, playing audio, flipping back to the front,
or repeating the same card does not add a unique card. Different card IDs in different
personal decks remain different cards, even if their text matches. Counts combine
sessions and devices for an account and learning language.

Milestones: **10, 100, 500, 1000**. First deck opened: once per account per consent period,
after successful loading and practice setup. Generation: successful mobile job completion,
recorded on the server even when the app is closed. Default content publication/download
is not a user generation event.

Store account ID, learning language, timestamp, event kind/milestone, and card IDs needed
for deduplication. No card text, deck title, email, password, location or advertising ID
in analytics. Account-linked, not anonymous. Unique card IDs are retained up to 1000 per
language while consent remains enabled. Events and retry receipts expire after 90 days
through a daily pg_cron job. Opt-out deletes events, identifiers and first-use markers;
a minimal consent preference remains. Offline revocation stops local collection immediately
and retries deletion on reconnect. Re-enabling starts a new measurement period.

Operational data is separate. No 90-day inactivity deck purge. Existing 14-day mobile
removal behavior remains for personal decks. Generation operational records currently
have no automatic expiry. Privacy wording must remain aligned with actual configuration.

Operator reporting example (privileged database access only):

```sql
select date_trunc('day', occurred_at) as day, kind, language, milestone,
       count(*) as events, count(distinct user_id) as accounts
from public.learning_events
group by 1,2,3,4 order by 1 desc,2,3,4;
```

These are consenting-account counts, not estimates for all users. The first-deck event
means first observed study after consent, not necessarily lifetime first study.

## Content workflow

The future production workflow is automated and fail-closed:

1. Read the pinned ranked corpus and form exactly 1,000 stable English concept slots. Reject
   fragments, isolated letters, abbreviations, codes and non-words (for example `de`). Keep every
   valid raw top-1,000 slot and fill each rejected slot with the next valid ranked English word.
   Write the complete decision trail to `concept_source` and `source_replacements.json`.
2. Reuse the existing English draft sentence only when it still belongs to the selected concept.
   A dedicated English editorial pass checks natural common usage, exact target-word inclusion,
   sense quality, CEFR suitability and meta/code examples; it makes the smallest needed revision.
3. Generate all 24 language/script options in ID-major blocks: IDs 1–20 across every language,
   then 21–40, and so on. Every language therefore retains the same concept ID, proposition,
   English sense and A1/A2/B1 membership. Thai script is completed before its Paiboon row.
4. For each target language, only ranks 1–1,000 of its pinned frequency list may supply frequency
   candidates or a `source_rank`. Frequency reorders cards within a level; it never changes the
   shared concept ID. A translated inflection with no exact ranked match remains explicitly null.
5. Google Cloud Translation supplies a first independent draft for supported target languages;
   GPT performs constrained post-editing. Content-bound source and target hashes prevent reuse
   after either side changes. Row-level checkpoints preserve valid completed work and purchase
   only missing or invalid cells. Before any paid request, production restores the current cache,
   merges the two durable generation artifacts (newest first), and enforces a 10,520-row raw
   checkpoint floor. A cache miss or missing artifact therefore stops the run instead of silently
   restarting. Only content-hash-compatible rows are reused. The per-run Google purchase ceiling
   is 500,000 new characters, and Google 429/500/502/503/504 failures use bounded backoff retries.
6. Automated adjudication repairs deterministic failures, then the network-free verifier checks
   every row against the pinned corpus and source manifest, checks scripts, senses, numbers,
   duplicates, rank limits and evidence hashes, and quarantines any failure. It alone creates the
   content-bound approval manifest; no API result can approve itself.
7. Generate SQL using `--output full --review review.json --version 1`. It rejects pilots,
   missing languages, duplicate concepts, wrong counts/ranks and stale approval hashes. Apply SQL
   in a controlled transaction. Published versions are immutable; corrections use a new version.

Concept IDs 1–400/401–700/701–1000 supply A1/A2/B1 membership. The set is the first 1,000
valid ranked English concepts after deterministic cleaning, not the first 1,000 raw tokens and
not a claim that literal translations are each language's 1,000 most frequent words. Later
updates preserve identity and level membership or require an explicit migration.

## Verification and rollout

- SQL integration tests: `npm install --no-save @electric-sql/pglite@0.5.8` then
  `node supabase/tests/learning_analytics.mjs`. Exercises thresholds, deduplication,
  opt-out/stale requests, expiry, generation and access restrictions using PostgreSQL WASM.
- Android CI: analyze, widget/unit tests and APK build. Local Flutter initialization was
  blocked by automatic approval review due to a metadata-endpoint request; do not bypass it.
- Before rollout: review pilot, validate full content, apply migrations and content, then
  check real-device account switching, offline downloads, consent, theme and drawer accessibility.
- pg_cron scheduling must be verified in Supabase after migration. WASM tests cover the cleanup
  function but do not provide pg_cron.
- Keep PR draft until complete content and physical-device checks are ready. iOS release paused.

Google Play provides install/activity/retention/conversion/crash reporting, not card-level
learning events: https://support.google.com/googleplay/android-developer/answer/139628?hl=en
Apple reporting: https://developer.apple.com/app-store-connect/analytics/
Update the store data declarations and public privacy policy before distributing this version.

## Verification checkpoint

Implementation PR: https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/pull/19

The first generated pilot failed content review: translated sentences retained English
headwords and Paiboon output mixed scripts. It must not be published. The corrected
pipeline uses explicit target-language fields, copied-headword detection, native-script
validation and Thai-to-Paiboon transliteration. The latest successful pilot workflow
uses GPT-4.1 for one-time editorial content after GPT-4o-mini pilot defects, and
provides a readable review table in its run summary and the downloadable artifact. The production
pipeline now also performs clean-source selection, selective English revision, ID-major generation,
content-bound checkpoint reuse and a final network-free publication gate as described above.

Android 0.6.0+12 is the development candidate. The README continues to link to the
previous published release until this candidate passes content and device review.

The mobile generation model remains GPT-4o-mini. The editorial pilot uses GPT-4.1
to improve alignment after observed headword and Thai transliteration failures.
This is a content-production experiment, not a claim that model output is publication-ready.
