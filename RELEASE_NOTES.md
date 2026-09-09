# Easy Language Learning Tool 1.4.1

Version 1.4.1 adds the renamed Easy Language Learning Tool Android companion and
publishes new Windows and Android installers together. It also adds an iOS companion
adaptation and publishes the native Mac DMGs through the production release workflow. Version
1.4.0 added native macOS application bundles and DMG installers for Apple
Silicon and Intel Macs while preserving the Windows edition and every v1.3.0
feature. Flashcard audio uses macOS `afplay`, bundled FFmpeg supports TTS without
a separate installation, credentials use macOS Keychain, and file deletion uses
Trash terminology. The Mac applications are ad-hoc signed and require Apple
Developer ID signing and notarization to remove the first-launch Gatekeeper warning.

## macOS

- Adds separate Apple Silicon and Intel DMG installers.
- Bundles Python, Qt, application resources, FFmpeg, and FFprobe.
- Adds native repeatable flashcard playback through `/usr/bin/afplay`.
- Uses macOS Keychain through the existing secure credential service.
- Uses platform-correct Trash labels and macOS application icons.
- Adds macOS build, bundle validation, launch smoke testing, checksum, and
  provenance gates to GitHub Actions and production releases.

## iOS companion preview 0.2.6

- Adapts the existing Flutter mobile companion to iPhone while preserving synchronized
  accounts, decks, history, list study, flashcards, and alternating two-language audio.
- Uses the established light/dark palette, shared application icon, secure Supabase callback,
  and iOS voice metadata for the selected female or male voice in both languages.
- Adds automated iOS configuration, tests, static analysis, a debug Simulator build, and an
  unsigned release-mode iPhone bundle with checksums and provenance.
- Requires Apple distribution signing and provisioning before installation on physical iPhones
  or TestFlight publication.

## Information

- Adds the Information tab after History.
- Embeds the complete Sentence Creation, Flashcards, TTS, History, connectivity,
  and troubleshooting guide in the standalone application and installer.
- Starts the embedded guide at section 1 and continues through section 6.
- Opens external documentation links in the system browser while keeping the
  manual itself available offline.

## Flashcards

- Adds a dedicated Flashcards tab for app-generated or schema-compatible `.xlsx`
  workbooks.
- Supports Words, Sentences, and combined Words and sentences modes. Combined
  cards show the larger bold word above the sentence on both sides.
- Uses the learning-language cells on the front and their translations on the
  back; the card surface and button both flip the card.
- Assigns rank 1 to the first data row below the header and stores every ranked
  row in the local SQLite backend without modifying the workbook.
- Supports inclusive From rank and To rank filtering through Selected rows only.
- Builds a random permutation with no repeated row before the eligible selection
  is exhausted. Previous and Next preserve the generated order; Shuffle again
  starts a fresh cycle without immediately repeating the current row.
- Persists the workbook checksum, indexed rows, mode, selected range, shuffled
  order, current position, and visible side across application restarts.
- Lets a workbook in History open directly in Flashcards.
- Redesigns the study surface around the supplied minimalist light/dark template:
  a near-full-tab card, substantially larger word and sentence text, a simple
  progress, compact language badge, and no side-name text bars or contrasting
  rectangles behind card text.
- Adds explicit **Load from History** and **Load from Desktop** actions to both
  Flashcards and TTS.
- Adds repeatable card audio for the visible side. It reuses matching individually
  generated TTS cell clips, lazily creates missing clips, persists them in the
  local cache, converts each playback result to a cached WAV, and uses native
  Windows playback so the same side can be played repeatedly.

## Mouse-wheel safety

- Closed dropdowns, numeric fields, and sliders always ignore wheel changes,
  including after an earlier click or keyboard focus.
- Ignored wheel input remains available to the containing page so normal page
  scrolling continues.
- Dropdown selection, spin buttons, slider dragging, and keyboard input remain
  usable.

## Existing production capabilities

- Seven spoken languages and eight language/script options, including Thai
  script and tone-marked Paiboon romanization.
- 40,000 ranked production records, deterministic CEFR/form/subject planning,
  provider-based generation, Excel-safe workbooks, resumable TTS, and safe local
  History.
- Globe-and-open-book Windows identity, bundled runtime and FFmpeg, Inno Setup
  packaging, checksum/provenance generation, and optional Authenticode signing.

The published v1.1.0 installer remains the public download until this release
candidate passes automated Windows acceptance and receives explicit approval.

## Android companion 0.2.3

- Audio mode now includes every selected learner-language word and sentence even when
  desktop TTS was not transferred.
- Transferred desktop clips remain preferred; missing or failed clips fall back per item
  to an installed Android text-to-speech voice.
- Learner-language speech matches the closest installed regional locale instead of
  failing when one exact locale is unavailable.
- Android 11+ release manifests explicitly declare text-to-speech service discovery.
- Flashcard audio uses the same adaptive voice fallback on both front and back.
- List view adds a scrollbar that appears during scrolling and fades afterward.

## Android companion 0.2.4

- Adds female and male phone-voice preferences to flashcard and audio setup.
- Adds a horizontal audio-speed adjustment with slow and fast endpoints, mapped to safe
  0.5×–2× playback for transferred clips and Android speech.
- Adds a default 0.5-second break between words and sentences, adjustable from 0 to 2 seconds.
- Makes the auto-hiding list scrollbar thicker and directly draggable for fast scrolling.

## Android companion 0.2.5

- Applies the selected male or female phone voice to both learning and translation languages;
  transferred fixed-voice clips are now fallback-only.
- Changes audio mode to alternate learning content and its translation for every selected word
  and sentence.
- Simplifies the speed control to a bare horizontal bar with −2× on its left and 2× on its
  right, removing the centre/current value and every label above the bar.

## Android companion 0.2.6

- Renames the visible Android application and launcher label to **Easy Language Learning Tool**.
- Keeps the existing package identity, local data, sign-in callback, and synchronized deck history compatible.
- Publishes the installable APK alongside the desktop installers in the v1.4.1 GitHub release.
