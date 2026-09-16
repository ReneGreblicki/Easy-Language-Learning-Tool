# Android Flashcards and Cross-Device Sync

## 1. Goal

Add an Android companion to Easy Language Learning Tool. Android can generate synchronized
decks through the protected cloud generation service and can study phone- or desktop-generated
decks through flashcards, a paired list, and resumable audio. Desktop remains the workbook and
desktop-TTS generator of record.

## 2. Locked product rules

1. A deck is saved locally on desktop before any upload is attempted.
2. Generation never depends on cloud availability.
3. Android keeps downloaded decks and audio offline.
4. **Remove download** removes only the Android device's local files.
5. Removing a phone download never modifies, archives, or deletes the desktop copy.
6. Removing a phone download never deletes the cloud recovery copy.
7. **Delete everywhere** is a separate, explicit, confirmed operation.
8. Delete everywhere soft-deletes the cloud copy for 30 days before permanent removal.
9. Desktop Trash applies only to deletion initiated in the desktop app. Phone actions never
   modify, archive, move, or delete desktop files.
10. Passwords are handled only by the authentication provider and are never stored by either app.
11. Desktop TTS upload and Android audio download are separate, explicit opt-in choices.
12. Opening the Android home library never downloads or resolves audio.
13. Release APKs must declare Android internet access in the main manifest; debug-only
    permissions are not accepted as release verification.
14. Android 11+ manifests must declare text-to-speech service discovery so installed
    learner-language engines and regional voices can be enumerated reliably.
15. Flashcard and audio setup must offer female and male phone-voice preferences. One selection
    applies to both learning and translation languages. Transferred clips are fallback-only
    because their fixed desktop voice cannot guarantee the selected phone gender.
16. **Generate a new deck** appears beneath the final deck in **My decks**, including when the
    library is empty.
17. Mobile generation uses the desktop language, row-count, extra-form, CEFR, question, and
    pronoun controls in a vertically scrolling phone layout.
18. Mobile users never choose or connect an AI provider and never enter an API key.
19. The AI provider key must never be compiled into the APK. It is stored as a Supabase Edge
    Function secret and accessed only after validating the signed-in user session.
20. A successfully generated deck is saved to the user's cloud library and downloaded to the
    generating phone. A failed or incomplete generation is not saved.
21. The Android home screen is a task-oriented landing page with actions for language, deck,
    generation, Flashcards, Audio, List, Further Learning, and Learning Instructions.
22. The selected learning language filters decks by `sourceLanguage`; translation language must
    never affect that filter.
23. Android remembers the last selected deck separately for each learning language. Switching
    languages restores a valid previous selection and never exposes a deck from another language.
24. Flashcards, Audio, and List share the active deck. When none is selected, the requested
    activity routes through the filtered deck picker and then continues to its existing setup.
25. A newly generated deck becomes the active deck and learning language automatically.
26. Further Learning collects media type, media-specific genre, CEFR level, and duration. The
    duration control is hidden for songs. External provider credentials remain server-side.
27. Learning Instructions presents the research-grounded app roadmap: high-frequency foundation,
    List comprehension, Flashcard retrieval, Audio listening/repetition, spaced review,
    understandable external input, active production, and functional progress checks.

## 3. Architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Desktop | Python, PySide6, SQLite | Generate decks and enqueue synchronization |
| Android | Flutter, SQLite | Phone generation, offline study, audio, progress, device-local removal |
| Generation API | Supabase Edge Function | Authenticate, enforce quotas and call the configured AI model |
| Identity | Supabase Auth | Email/password authentication and recovery |
| Cloud data | Supabase PostgreSQL | User-owned decks, cards, progress and sync metadata |
| Cloud files | Supabase Storage | User-owned flashcard audio |
| Security | PostgreSQL RLS | Prevent cross-user access |

A unique username is stored in the profile. Authentication uses email/password so password
recovery remains reliable. Username sign-in can be added later through a protected server
function without exposing account lookup data.

## 4. Synchronized data

- Deck identity, title, language, CEFR level and generation settings
- Ranked cards: foreign word, word translation, foreign sentence, sentence translation
- Audio object metadata and checksums
- Study selection, shuffled order, current position and session history
- Revision, source device and synchronization timestamps
- Global soft-deletion state

Device-local download state is never synchronized as a deck deletion. It is stored in the
Android database under the device installation ID.

## 5. Data lifecycle

### Desktop generation

1. Generate and validate the workbook.
2. Save the workbook and flashcard source locally.
3. Assign stable UUIDs to the deck and cards.
4. Add an upsert operation to the durable outbox.
5. Upload metadata and cards.
6. If **Include available desktop TTS audio** is enabled, discover matching cached word and
   sentence clips and upload them to private user storage with checksums.
7. Mark each outbox operation complete only after server acknowledgement.

### Android generation

1. Sign in and select **Generate a new deck** beneath the deck list.
2. Enter the deck name and choose learning language, translation language, base words, extra
   forms, CEFR configuration, question percentage, and pronoun-change scale.
3. Load the packaged production frequency ranking and build the deterministic row plan locally.
4. Send batches of at most 20 planned rows to the JWT-protected generation function.
5. The function validates the session and request, enforces the per-user quota, and calls the
   server-configured AI model without returning or exposing its API key.
6. Validate every returned row and save only a complete deck.
7. Insert the deck and cards into the user's RLS-protected cloud records, then save the same deck
   in the phone's offline cache.
8. Refresh **My decks** with the new deck above the generation button.

### Android download

1. Authenticate.
2. Read changes after the last server cursor.
3. Store metadata and cards in one local transaction.
4. Present activity choice, then content/range settings.
5. Resolve audio only for audio-capable activities; prefer transferred clips and use the
   closest installed Android learner-language voice when a clip is absent or fails.
6. Download audio only when the user explicitly enables offline audio.
7. Mark deck text available offline.

### Android landing and activity workflow

1. Select a learning language from the landing page.
2. Select a matching deck or generate a new one.
3. Choose **Practice flashcards**, **Practice audio**, or **Practice list**.
4. If no valid deck is active, select one from the language-filtered picker and continue.
5. Choose Words, Sentences, or both.
6. Choose all rows or an inclusive rank range.
7. Optionally download transferred desktop audio for offline use.
8. Flashcards use two sides and an invisible 75% anchor for the sound button.
9. Audio playback alternates learning and translation items within each selected row and
   persists position by deck, mode, and range. Its horizontal speed control shows only −2×
   to the left and 2× to the right; the normal centre is unlabelled. Its inter-item break
   defaults to 0.5 seconds with selectable values from 0 to 2 seconds.
10. List view renders each foreign value immediately above its translation and uses an
   auto-hiding, draggable scrollbar that appears only during scrolling.

### Learning roadmap

1. Choose one learning language and a practical comprehension or communication goal.
2. Generate a manageable high-frequency foundation, initially about 100–300 rows at A1.
3. Understand new rows in List before testing them.
4. Attempt active recall before pressing **Turn** in Flashcards.
5. Use Audio to listen without text, recall meaning, hear the translation, and repeat aloud.
6. Review across expanding intervals; shorten intervals after failed recall.
7. Use Further Learning to choose understandable external material near the current CEFR level.
8. Produce original speech or writing with studied vocabulary.
9. Judge progress through recall, listening recognition, unfamiliar-context comprehension,
   original production, and the ability to summarize suitable media.

Suggested row counts and review intervals are practical starting points, not fixed scientific
optima. Android does not claim to implement automatic spaced repetition until a scheduling model
and review queue are explicitly added.

### Study progress

1. Save each interaction locally first.
2. Add the progress update to the outbox.
3. Merge independent card progress fields.
4. Resolve same-field conflicts using revision followed by server timestamp.

### Remove download

1. Confirm local removal.
2. Delete Android-local card/audio files for that deck.
3. Retain a lightweight cloud-library reference.
4. Do not emit a cloud deck-delete event.
5. Allow the user to download the deck again.

### Delete everywhere

1. Require explicit confirmation.
2. Set cloud `deleted_at` and create a deletion marker.
3. Leave the original desktop workbook and desktop records unchanged.
4. Hide/remove downloaded copies on connected phones.
5. Permit restoration for 30 days.
6. Permanently remove records and audio after retention expires.
7. Retain a tombstone long enough to stop stale offline devices recreating the deck.

## 6. Delivery phases

Current implementation status: Phases A–C and the synchronization foundation from Phase D are
implemented on the draft release branch. Automated Windows, macOS, Python, and Android gates
run for every checkpoint. Release signing, store publication, and physical-device verification
remain human-gated Phase E work.

### Phase A — Contracts and cloud foundation

- Versioned synchronization payloads
- Supabase migration, constraints, indexes and RLS
- Storage ownership policy
- Device registration and cursors
- Soft deletion and tombstones

### Phase B — Desktop synchronization

- Account/session service
- Stable deck/card UUIDs
- Durable outbox
- Push/pull client with retries
- Sync status and error reporting
- Account, device and Trash UI

### Phase C — Android offline MVP

- Registration, login, logout and password reset
- Cloud deck library
- Download/remove-download actions
- Local SQLite cache
- Desktop-matched two-sided flashcard study
- Words, Sentences, or combined content selection
- All rows or inclusive selected-rank range
- Previous, Turn, Next, Reshuffle and in-card audio controls
- Desktop-matched light/dark palettes and application icon
- Landing-page practice action followed by activity-specific settings
- Paired, colour-coded list view
- Desktop TTS audio transfer as an explicit opt-in
- Resumable word/sentence/combined audio playlists
- Audio timeout recovery and invisible sound-button positioning anchor
- Central user-facing error translation for authentication, network, sync, storage, and audio
- Generate-new-deck action on the landing page
- Phone-scaled desktop-equivalent generation settings
- Packaged production frequency data and deterministic row planning
- JWT-protected server generation with per-user quota enforcement
- Atomic cloud save followed by local offline caching
- Task-oriented landing page and per-language active-deck state
- Language-filtered deck selection and activity continuation routing
- Further Learning preference form
- In-app learning roadmap

### Phase D — Bidirectional progress sync

- Incremental cursors
- Offline outbox
- Idempotent writes
- Conflict handling
- Multi-device test matrix

### Phase E — Release hardening

- Accessibility review and theme persistence
- Network interruption and storage-pressure recovery
- Security and privacy review
- Android App Bundle signing
- Internal Play Store testing
- User manual and support documentation

## 7. Test workflow

Every pull request must run:

1. Formatting, linting, static analysis and secret scanning.
2. Desktop unit/integration tests.
3. SQL schema and RLS policy tests.
4. Flutter analysis and unit/widget tests.
5. Synchronization contract compatibility tests.
6. Offline, retry, duplicate-event and conflict tests.
7. Device-local removal test proving cloud and desktop records remain unchanged.
8. Delete-everywhere restoration and retention tests.
9. Optional audio upload/download tests and audio-session resume tests.
10. Landing activity routing, list ordering/colour, and flashcard loading-state widget tests.
11. Error-message tests proving raw exceptions, server URLs, and internal codes are not displayed.
12. Generated release-manifest tests proving Supabase network access is declared.
13. Mobile generation validation, 5,000-row limit, deterministic planning, button placement,
    authentication, quota, incomplete-response, cloud-save, and local-cache tests.
14. Landing-page action, learning-language filter, per-language deck restoration, missing-deck
    continuation, generated-deck activation, Further Learning conditional-duration, and Learning
    Instructions navigation tests.

Release candidates additionally require:

- Windows and macOS regression builds
- Android installable release APK build
- Android release AAB build
- Clean Android installation
- Offline deck and audio test
- Two-device synchronization test
- Real-device notification, lifecycle and storage tests

## 8. Human verification gate

Development proceeds automatically until credentials or physical-device verification is needed.
The human gate requires:

- Supabase project URL and public anonymous key
- Protected GitHub secrets `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, and
  `OPENAI_API_KEY`; `OPENAI_MODEL` is optional
- Successful manual **Deploy mobile deck generation** workflow execution, applying the
  Supabase migration and deploying the `generate-deck` Edge Function
- Android application ID approval
- Tests on at least one supported Android phone
- Google Play developer account and signing decision for publication

## 9. Definition of done

- Desktop-generated decks synchronize without risking local generation output.
- Downloaded Android decks work completely offline.
- Study progress synchronizes deterministically.
- Remove download affects only that Android installation.
- Desktop data remains unchanged after phone-only removal.
- Delete everywhere is recoverable for 30 days.
- RLS isolation and synchronization tests pass.
- Signed Android release is installable and documented.
- Phone generation exposes no provider configuration or reusable provider secret.
- A complete generated deck appears in cloud sync and remains available offline on its phone.


## 10. iOS parity extension

The shared Flutter study client is also adapted for iOS. Apple-specific bundle identity,
Supabase callback registration, icon generation, deployment target, voice identifiers, simulator
packaging, signing requirements, and acceptance gates are defined in
`docs/APPLE_PLATFORM_PLAN.md`. Android deletion and synchronization rules apply unchanged to
iOS: removing a download is device-local and never changes desktop files.
