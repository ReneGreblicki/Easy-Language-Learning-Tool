# Easy Language Learning Tool 1.1.0

Version 1.1.0 adds complete Thai support and repairs Windows application identity
and icon packaging.

## Thai support

- Adds Thai as the seventh supported spoken language.
- Adds two explicit learning and translation options:
  - Thai (Thai script)
  - Thai (Paiboon romanization)
- Includes 5,000 ranked, validated entries for each Thai option, bringing the
  production corpus to 40,000 records across eight language/script options.
- Uses the CC BY-SA OpenSubtitles 2018 ranking, the CC0 Phupha 2026 frequency
  dataset, and Kaikki/Wiktionary lexical and tone-marked romanization data.
- Uses Thai Microsoft Edge neural voices for both Thai options.
- Locks prompts so the Thai-script option stays in Thai script and the Paiboon
  option stays in tone-marked Latin romanization.

The supplied Lenguia and 1000MostCommonWords.com pages remain comparison sources
because they do not grant redistribution rights. The supplied Scribd list is
marked All Rights Reserved and is not bundled.

## Windows identity and branding

- Replaces the previous logo with a globe rising from an open book.
- Adds a native multi-resolution Windows `.ico` and matching high-resolution PNG.
- Embeds the icon directly into the Nuitka executable.
- Applies the icon to the running Qt application, title bar, taskbar card,
  installer, Start menu shortcut, desktop shortcut, and uninstall entry.
- Sets an explicit Windows AppUserModelID so the taskbar groups the running app
  under the installed application identity instead of displaying a generic icon.

## Existing production capabilities

- Deterministic 5,000-word selection, CEFR planning, exact question allocation,
  neutral/personal subject controls, and part-of-speech-aware extra forms.
- OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom compatible providers.
- Excel-safe workbooks, checkpointed generation, resumable Edge TTS, safe local
  History, bundled FFmpeg, and per-user Windows installation.
- Automated formatting, linting, strict typing, corpus validation, Windows UI,
  packaged launch, install, upgrade/repair, uninstall, checksum, and provenance
  gates.

Authenticode signing remains automatic when both protected publisher-certificate
secrets are configured. Unsigned builds may display a Windows Unknown Publisher
warning.
