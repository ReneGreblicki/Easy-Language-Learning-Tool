# Android Flashcards and Cross-Device Sync

## 1. Goal

Add an Android study companion to Easy Language Learning Tool. The desktop remains the
generator of record. Android offers flashcards, a paired list, and resumable playback of
desktop-generated TTS audio.

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

## 3. Architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Desktop | Python, PySide6, SQLite | Generate decks and enqueue synchronization |
| Android | Flutter, SQLite | Offline study, audio, progress, device-local removal |
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

### Android download

1. Authenticate.
2. Read changes after the last server cursor.
3. Store metadata and cards in one local transaction.
4. Present activity choice, then content/range settings.
5. Stream audio only for audio-capable activities.
6. Download audio only when the user explicitly enables offline audio.
7. Mark deck text available offline.

### Android activity workflow

1. Select a deck from the unchanged **My decks** home page.
2. Choose **Flashcards**, **Listen to audio**, or **View list**.
3. Choose Words, Sentences, or both.
4. Choose all rows or an inclusive rank range.
5. Optionally download transferred desktop audio for offline use.
6. Flashcards use two sides and an invisible 75% anchor for the sound button.
7. Audio playback persists position by deck, mode, and range.
8. List view renders each foreign value immediately above its translation.

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
- Activity chooser followed by activity-specific settings
- Paired, colour-coded list view
- Desktop TTS audio transfer as an explicit opt-in
- Resumable word/sentence/combined audio playlists
- Audio timeout recovery and invisible sound-button positioning anchor

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
10. Activity chooser, list ordering/colour, and flashcard loading-state widget tests.

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
