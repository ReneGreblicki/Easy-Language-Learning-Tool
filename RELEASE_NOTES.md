# Easy Language Learning Tool 1.4.0 RC

Version 1.4.0 adds native macOS application bundles and DMG installers for Apple
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
