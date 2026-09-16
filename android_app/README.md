# Easy Language Learning Tool mobile app

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
the Supabase SQL editor. Mobile generation, current media recommendations, and retention cleanup
additionally require deployment of `../supabase/functions/generate-deck`, `recommend-media`, and
`deck-maintenance`, plus these Supabase project secrets:

```text
OPENAI_API_KEY=<server-side provider key>
OPENAI_MODEL=gpt-5-mini
```

`OPENAI_MODEL` is optional. The provider key is intentionally absent from Flutter assets,
Dart defines, logs, and the APK. The Edge Function validates the signed-in user and enforces a
5,000-row rolling 24-hour quota before calling the provider. Generation is persisted server-side,
processes multiple batches concurrently, and continues when the app is closed.

For automated deployment, add `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, and
`OPENAI_API_KEY` as protected GitHub Actions secrets. Optionally add `OPENAI_MODEL`.
Run **Deploy mobile deck generation** manually; it applies pending migrations, configures the
server-only provider secret, and deploys the authenticated function.

Then open **Authentication → URL Configuration** and add this redirect
URL:

```text
com.renegreblicki.easylanguageflashcards://login-callback/**
```

Confirmation and password-recovery emails then reopen the Android or iOS app instead of redirecting
to `localhost`.

## Current deletion behavior

- **Remove download** immediately deletes this mobile installation's cached deck and audio.
- The synchronized mobile deck is hidden and scheduled for complete Supabase cleanup after 14 days.
- Reusing or downloading the deck during that period cancels cleanup.
- Desktop workbooks and desktop-local files remain unchanged.

## Mobile landing page and navigation

- A phone-scaled landing page provides **Select a language**, **Select a deck**,
  **Generate a new deck**, three practice modes, **Further learning**, and
  **Learning instructions**.
- Selecting a language filters the deck picker by the deck's learning language.
- The active deck is shared by Flashcards, Audio, and List, while the last active deck is
  remembered separately for each language.
- Opening a practice mode without an active deck first opens the filtered deck picker and then
  continues to the requested setup screen.
- Background generation status appears on the landing page and the completed deck is refreshed
  automatically.
- Further learning requests exactly three current GPT/web-search-backed options with a title,
  description, direct link, and optional image. Duration is omitted for songs and movies and is
  labelled **Episode duration** for series.
- Learning instructions present the in-app cycle: List → Flashcards → Audio → spaced review →
  suitable external media → active language use.

## Implemented generation and study behavior

- Generate a new deck from the main landing page
- Phone-scaled desktop-equivalent language, starting frequency rank, count, forms, CEFR,
  question, and pronoun controls with automatic maximum-row clamping
- No mobile provider selector, provider connection, or API-key field
- Authenticated persistent server-side generation with concurrent provider batches
- Full intermediate settings page for every Flashcards, Audio, and List launch
- Ten active decks per learning language
- `last_used_at` tracking prepared for, but not yet enforcing, a future 90-day inactivity policy
- Flashcards, resumable audio playback, and paired list view
- Launch choice: Words, Sentences, or Words and sentences
- Launch choice: all rows or an inclusive selected rank range
- Two-sided cards: learning content on the front and translation on the back
- Tap the card or press Turn to flip it
- Previous, Turn, Next, and Reshuffle controls
- Large sound control centered at 75% card height with no visible guide line
- Adaptive device text-to-speech for both learning and translation languages, with
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


## iOS development and testing

The repository generates the iOS Xcode shell during CI so Flutter's current platform template
stays reproducible. Run these commands on macOS with Xcode installed:

```bash
cd android_app
flutter create --platforms=ios --org com.renegreblicki .
python3 tool/configure_ios.py
flutter pub get
flutter run
```

The configuration step registers the existing Supabase callback scheme, sets the bundle
identifier to `com.renegreblicki.easylanguagelearningtool`, installs the desktop artwork in
the iOS icon catalog, and targets iOS 13 or newer. The same Supabase redirect URL used by
Android must remain configured.

CI publishes an unsigned iOS Simulator application for automated and developer testing.
Installing on a physical iPhone, distributing through TestFlight, or publishing in the App
Store requires an Apple Developer team, an Apple Distribution certificate, and a provisioning
profile.
