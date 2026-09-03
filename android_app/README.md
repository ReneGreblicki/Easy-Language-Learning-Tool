# Easy Language Flashcards for Android

## Development build

The Supabase publishable key is intentionally not committed. Supply configuration at build time:

```bash
flutter run \
  --dart-define=SUPABASE_URL=https://jmnsrikmqopdhmnkjmah.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=your_publishable_key
```

The publishable key is designed for client applications. Database security depends on the
row-level security policies in `../supabase/migrations/0001_android_sync.sql`, not on hiding
the publishable key.

Before connecting the app, execute
`../supabase/migrations/0001_android_sync.sql` in the Supabase SQL editor. This creates the
tables, account-profile trigger, private audio bucket, indexes and row-level security policies.

## Current deletion behavior

- **Remove download** deletes only this Android installation's cached deck and audio.
- The cloud and desktop copies remain unchanged.
- **Delete everywhere** is a separate cloud operation and is not exposed without confirmation.
