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

1. `tools/build_default_decks.py --pilot --output draft --languages en-US es-ES de-DE th-Thai-TH th-Latn-TH`.
   Thirty concepts, ten from each level; GitHub pilot workflow uses the existing OpenAI secret.
2. Review sense alignment, naturalness, target-word use, CEFR difficulty and Thai script/romanization.
3. Generate full curriculum with `--output full` (all 24 supported options by default).
   Checkpoints prevent regenerating completed batches. Source SHA and attribution are embedded.
4. Resolve unmatched source ranks and duplicate/ambiguous translations. Automated checks do not
   replace language review. Frequency determines ordering within levels, not CEFR certification.
5. Record explicit review in JSON: `{"sha256":"<curriculum file SHA256>","reviewer":"<reviewer>","approved":true}`.
6. Generate SQL using `--output full --review review.json --version 1`. It rejects pilots,
   missing languages, duplicate concepts, wrong counts/ranks and a stale review hash.
7. Apply the SQL in a transaction using the controlled database publication process. Published
   versions are immutable; choose a new version for corrections. Stable card IDs preserve progress.

English entries 1–400/401–700/701–1000 supply the initial level group allocation. This is a
shared English-concept curriculum, not a claim to contain each language's top 1000 words.
Adjust curriculum membership after review before first publication. Later updates must
preserve level membership and identity, or use an explicit migration.

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
