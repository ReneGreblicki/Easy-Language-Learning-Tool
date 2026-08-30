# Easy Language Learning Tool 1.0.0

Easy Language Learning Tool 1.0.0 is the first production release of the Windows
desktop application for deterministic language-learning sentence workbooks and
resumable text-to-speech audio.

## Production capabilities

- Six learning and translation languages: US English, European Spanish, German,
  European Portuguese, French, and Italian.
- Exactly 5,000 ranked words per language across all parts of speech, selected
  deterministically by the application from the attributed wordfreq baseline.
- Part-of-speech-aware extra forms with a hard 5,000-row output limit.
- CEFR A1-C2 planning, exact question allocation, and deterministic
  neutral-to-personal subject-structure controls.
- OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom OpenAI-compatible
  providers with model discovery, cost estimates, targeted retry, checkpointing,
  and resume.
- Excel-safe XLSX and CSV output with four public study columns and audit metadata,
  including backward-compatible imports for earlier verb workbooks.
- Edge neural TTS with separate voices, four configurable pauses, two-row preview,
  combined MP3 export, pause/cancel, partial recovery, and checksum-safe resume.
- Safe local History with independent retention for workbooks and audio, protected
  app-owned file operations, and Windows Recycle Bin deletion.
- Light and dark themes, a centered responsive PySide6 interface, bundled runtime,
  bundled FFmpeg, and a normal per-user Windows installer.

## Final changes since 0.5.0 RC

- Promoted the fully validated release candidate to version 1.0.0.
- Added an automated version-alignment regression gate for Python metadata,
  installer metadata, documentation, and release notes.
- Added tag-driven production publishing that verifies the corpus, repeats tests,
  builds the Windows package, downloads the verified artifact, and publishes the
  installer, checksum, provenance, and portable archive to GitHub Releases.
- Recorded the completed automated and clean-client acceptance gates in the
  maintained project documentation.

## Release integrity

The production workflow enforces the six-language 30,000-record corpus gate,
quality and security checks, the full automated test suite, packaged launch,
silent install, upgrade/repair, uninstall, bundled-resource checks, user-data
preservation, SHA-256 generation, and build provenance.

Authenticode signing is enabled automatically when both protected Windows signing
secrets are configured. Public binary distribution should use the signed workflow
artifact; source releases and pull-request test artifacts may remain unsigned.
