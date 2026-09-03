# Release readiness

## Automated release gates

- Ruff formatting and lint pass.
- Strict mypy checking passes.
- Unit, provider-contract, workbook, ranked-flashcard, History, and mocked-TTS tests pass.
- Subject-structure tests prove fully neutral option 0, exact 20% increments for
  options 1–4, deterministic assignments, and no consecutive pattern repetition
  for option 5 across all final rows.
- Windows UI smoke test opens all four tabs and validates the 50% launch size.
- Windows UI smoke checks European Spanish → US English defaults, unambiguous
  dataset wording, calculated-row placement, and contextual scale help.
- Flashcard gates verify header-free continuous ranks, three display modes,
  inclusive filtering, no repeats within a shuffle cycle, previous/next order,
  restart persistence, History loading, and read-only source workbooks.
- Wheel-safety gates verify that dropdowns, number fields, and sliders never
  change from page-scrolling wheel input, even after a prior click, and that the
  event remains available to page scrolling.
- Flashcard playback gates verify cached WAV conversion and repeated native
  playback of the same card side.
- Windows build contains the Python/Qt runtime, application resources, FFmpeg,
  FFmpeg notices, the README, and the example workbook.
- Inno Setup produces a normal per-user installer.
- The compiled installer is silently installed into a path containing spaces and
  Unicode, launched, installed again to exercise upgrade/repair, and uninstalled.
- Automated installer acceptance verifies bundled resources and preservation of
  app-owned user data across upgrade and uninstall.
- The installer artifact receives a SHA-256 checksum.

## Frequency-data gate

The repository contains an attributed, reproducible wordfreq production baseline
and a smaller multi-POS demonstration fixture. `tools/check_release_data.py` must
report exactly 5,000 ranked, source-attributed word entries for each of eight
supported language/script options before packaging.

Production data must preserve rank, lemma, part of speech, forms, translations,
confidence, source, licence, source URL, revision, and automated-validation state.
Dictionary translations and POS/form evidence are retained when available. A
blank baseline translation is supplied and validated by the generation provider.
Ranks must be contiguous and normalized lemmas unique. The UI exposes only the
four agreed workbook columns.

Canonical ranking uses wordfreq for the original six languages. Thai ranking uses
OpenSubtitles 2018 and the CC0 Phupha 2026 dataset; Kaikki/Wiktionary validates
lexical entries and supplies tone-marked Paiboon romanization. The three supplied
Thai pages are comparison-only because one is all-rights-reserved and the others
do not provide compatible redistribution terms. No human linguistic approval gate
is required.

## External release operations

Code signing and Microsoft Defender/SmartScreen reputation require a publisher
identity and signing certificate. The unsigned installer can be built and tested
without them, but public distribution should use a signed installer. The Windows
workflow signs both the standalone executable and installer when the repository
secrets `WINDOWS_SIGNING_CERTIFICATE_BASE64` and
`WINDOWS_SIGNING_CERTIFICATE_PASSWORD` are configured, verifies each Authenticode
signature, and records signing state in `BUILD_PROVENANCE.txt`.

GitHub-hosted Windows acceptance is an automated packaging gate, not a substitute
for the final clean Windows 10 and Windows 11 client-machine acceptance record.

The 1.1.0 acceptance record confirms clean-client installation, launch,
upgrade/repair, uninstall, shortcuts, bundled FFmpeg, and preservation of
user-owned exports on Windows 10 and Windows 11. The production tag workflow
repeats the automated gates and publishes the installer, checksum, provenance,
and portable archive. Authenticode signing remains conditional on the protected
publisher certificate secrets because publisher identity cannot be stored in
source control.

The 1.3.0 release candidate must additionally pass database-v1 migration,
flashcard restart recovery, Windows mouse-wheel interaction tests, and packaged
Information-guide availability and numbering checks. Its draft
branch and workflow artifact are not a public release. The v1.1.0 release, README
download target, and GitHub `main` remain unchanged until explicit approval.
