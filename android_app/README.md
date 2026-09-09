# Easy Language Learning Tool for Android

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

The platform-configuration step explicitly adds `android.permission.INTERNET` to the main
manifest used by release APKs. Do not rely on Flutter's debug-only manifest: debug builds can
connect even when a release build has no network permission.

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
- Flashcards, resumable audio playback, and paired list view
- Launch choice: Words, Sentences, or Words and sentences
- Launch choice: all rows or an inclusive selected rank range
- Two-sided cards: learning content on the front and translation on the back
- Tap the card or press Turn to flip it
- Previous, Turn, Next, and Reshuffle controls
- Large sound control centered at 75% card height with no visible guide line
- Adaptive Android text-to-speech for both learning and translation languages, with
  transferred desktop audio retained as an offline fallback
- Audio-player entries exist even when desktop audio was not transferred
- One female or male phone-voice selection applied to both languages
- Paired audio order: learning item, translation, learning item, translation
- Audio speed bar with only −2× and 2× endpoint labels; its normal centre is unlabelled
- Configurable inter-item break from 0 to 2 seconds, defaulting to 0.5 seconds
- Auto-hiding, draggable list scrollbar that is visible only while scrolling
- Descriptive authentication, network, synchronization, storage, and audio errors without
  exposing raw exception details or server URLs
- Switchable desktop-matched light and dark palettes
- The same launcher artwork as the desktop application
