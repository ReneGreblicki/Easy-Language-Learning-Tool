# Release readiness

## Automated release gates

- Ruff formatting and lint pass.
- Strict mypy checking passes.
- Unit, provider-contract, workbook, History, and mocked-TTS tests pass.
- Windows UI smoke test opens all three tabs and validates the 50% launch size.
- Windows build contains the Python/Qt runtime, application resources, FFmpeg,
  FFmpeg notices, the README, and the example workbook.
- Inno Setup produces a normal per-user installer.
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
without them, but public distribution should use a signed installer.
