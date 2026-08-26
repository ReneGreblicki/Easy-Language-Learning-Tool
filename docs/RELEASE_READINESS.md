# Release readiness

## Automated release gates

- Ruff formatting and lint pass.
- Strict mypy checking passes.
- Unit, provider-contract, workbook, History, and mocked-TTS tests pass.
- Subject-structure tests prove fully neutral option 0, exact 20% increments for
  options 1–4, deterministic assignments, and no consecutive pattern repetition
  for option 5 across all final rows.
- Windows UI smoke test opens all three tabs and validates the 50% launch size.
- Windows UI smoke checks European Spanish → US English defaults, unambiguous
  dataset wording, calculated-row placement, and contextual scale help.
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
report exactly 5,000 ranked, source-attributed word entries for each of the six
supported languages before packaging.

Production data must preserve rank, lemma, part of speech, forms, translations,
confidence, source, licence, source URL, revision, and automated-validation state.
Dictionary translations and POS/form evidence are retained when available. A
blank baseline translation is supplied and validated by the generation provider.
Ranks must be contiguous and normalized lemmas unique. The UI exposes only the
four agreed workbook columns.

Canonical ranking uses wordfreq; Kaikki/Wiktionary provides lexical enrichment.
The supplied third-party pages are comparison sources unless their redistribution
terms are explicitly compatible. No human linguistic approval gate is required.

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
