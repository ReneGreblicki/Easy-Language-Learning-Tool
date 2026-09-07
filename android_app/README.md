# Easy Language Flashcards for Android

## Development build

The Supabase publishable key is bundled with the client, as intended for Supabase public client
keys. It may be overridden at build time:

```bash
flutter run \
  --dart-define=SUPABASE_URL=https://jmnsrikmqopdhmnkjmah.supabase.co \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=your_publishable_key
```

The publishable key is not a service-role secret. Database security depends on the
row-level security policies in `../supabase/migrations/0001_android_sync.sql`, not on hiding
the publishable key.

Before connecting the app, execute every file in `../supabase/migrations` in numeric order in
the Supabase SQL editor. Then open **Authentication → URL Configuration** and add this redirect
URL:

```text
com.renegreblicki.easylanguageflashcards://login-callback/**
```

Confirmation and password-recovery emails then reopen the Android app instead of redirecting
to `localhost`.

## Current deletion behavior

- **Remove download** deletes only this Android installation's cached deck and audio.
- The cloud and desktop copies remain unchanged.
- **Delete everywhere** is a separate cloud operation and is not exposed without confirmation.

## Implemented study behavior

- Four sides in order: foreign word, word translation, foreign sentence, sentence translation
- Tap the card to advance between sides
- Previous and next navigation
- Known, Learning and Difficult ratings
- Local-first progress persistence
- Repeatable audio playback when an audio URL is available
