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

- Two-stage deck launch: activity first, then content and row settings
- Flashcards, resumable desktop-audio playback, and paired list view
- Launch choice: Words, Sentences, or Words and sentences
- Launch choice: all rows or an inclusive selected rank range
- Two-sided cards: learning content on the front and translation on the back
- Tap the card or press Turn to flip it
- Previous, Turn, Next, and Reshuffle controls
- Large sound control centered at 75% card height with no visible guide line
- Downloaded audio when available, with Android text-to-speech as a fallback
- Descriptive authentication, network, synchronization, storage, and audio errors without
  exposing raw exception details or server URLs
- Switchable desktop-matched light and dark palettes
- The same launcher artwork as the desktop application
