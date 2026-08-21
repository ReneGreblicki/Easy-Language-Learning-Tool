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

The repository contains a small, attributed demo corpus so the data contract and
pipeline can be tested. It is intentionally not labelled production-ready.

A public installer must not be released until `tools/check_release_data.py`
reports at least 4,000 unique, source-attributed verb lemmas for each of the five
supported languages. This prevents unreviewed words, model-invented rankings, or
licence-unclear example material from being presented as a frequency baseline.

Approved production data must preserve rank, lemma, translations, irregularity,
supported constructions, confidence, source, and licence in each internal
record. It must also preserve the source URL and revision plus the reviewer,
review date, and approval state. Every approved verb needs a non-empty
translation into all four other supported languages. The UI exposes only the
four agreed workbook columns.

## External release operations

Code signing and Microsoft Defender/SmartScreen reputation require a publisher
identity and signing certificate. The unsigned installer can be built and tested
without them, but public distribution should use a signed installer.
