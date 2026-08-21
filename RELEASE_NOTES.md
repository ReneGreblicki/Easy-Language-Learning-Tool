# Easy Language Learning Tool 0.3.0 — internal release candidate

## Frequency-data workflow

- Added Kaikki/Wiktionary verb-candidate extraction with deterministic
  `wordfreq` ranking, form filtering, duplicate removal, translation capture,
  construction metadata, and usage/locale review flags.
- Added a TSV audit tool and human-approval metadata required by the production
  release gate.
- Strengthened the release gate to reject missing translations, duplicate or
  discontinuous ranks, incomplete attribution, missing constructions, and
  unapproved records.
- The interface now identifies the bundled dataset and caps base sentences to
  the number of usable translated verbs, preventing the four-verb demonstration
  build from accepting unsupported jobs.
- Added Wiktionary/Kaikki licensing and attribution documentation.

## Workbook compatibility fix

- Removed the redundant OOXML Table part that Microsoft Excel repaired on open.
- Kept worksheet AutoFilter, frozen headers, column sizing, and header styling.

## Included

- Complete three-tab PySide6 desktop interface with centered 50% launch,
  responsive scrolling, and Power BI-inspired light/dark themes.
- OpenAI, Anthropic, Google Gemini, DeepSeek, Ollama, and custom
  OpenAI-compatible provider adapters with model discovery and normalized errors.
- Windows Credential Manager support, session-only key fallback, redacted logs,
  transient network retry, and sourced model-cost estimates.
- Deterministic CEFR, question/statement, pronoun, verb-rank, and extra-form plan.
- Structured batched generation, validation, targeted retry, and resumable checkpoints.
- Canonical XLSX/CSV services and an installer-ready example workbook.
- Edge neural TTS with exact two-row preview, dynamic locale voice discovery,
  four pause controls, partial MP3 preservation, and checksum-safe continuation.
- SQLite-backed History with independent 20-file retention, Recycle Bin deletion,
  safe rename/export, regeneration settings, and partial-audio export.
- SVG logo, locked dependencies, 85% coverage gate, Windows UI/package tests,
  Nuitka standalone build, bundled FFmpeg, Inno Setup installer, and SHA-256 output.

## Verified reference compatibility

- The supplied 1,000-row German workbook imports successfully.
- The supplied reference audio is a valid MP3 and remains reference material only.
- The supplied German Audio Maker archive informed the TTS workflow but is not
  copied into the new application.

## Public-release gates

- Add and linguistically review at least 4,000 unique, attributed verb lemmas for
  every supported language. The release workflow enforces this automatically.
- Run the live five-language linguistic suite and protected-provider smoke tests.
- Build on clean Windows 10 and Windows 11 VMs and complete install/upgrade/uninstall tests.
- Apply the publisher's code-signing certificate and complete Defender/SmartScreen checks.

Internal installers can be built before those public-release gates, but must not
be described as the final public dataset release.
