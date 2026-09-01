# Easy Language Learning Tool 1.2.0 RC

Version 1.2.0 adds ranked, resumable workbook flashcards and prevents accidental
mouse-wheel changes to application settings. This release candidate remains on a
draft branch until explicit release approval; the published v1.1.0 installer is
unchanged.

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

## Mouse-wheel safety

- Dropdowns, numeric fields, and sliders ignore wheel changes until the exact
  control has been clicked.
- An unfocused control passes wheel input to the containing page so normal page
  scrolling continues.
- Clicking another control or page background disarms the previous field.
- Open dropdowns, keyboard navigation, and explicitly focused controls remain
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
