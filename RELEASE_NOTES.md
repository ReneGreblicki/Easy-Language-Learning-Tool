# Easy Language Learning Tool 0.5.0 — sentence-structure release candidate

## Changed since 0.4.0

- Defaulted both Sentence Creation and TTS to European Spanish as the learning/foreign
  language and US English as the translation language.
- Reworded the dynamic dataset notice to distinguish the ranked learning-language words,
  AI-generated learning-language examples, translated examples, and AI-generated missing
  word translations.
- Moved the calculated final-row count directly below the Extra word forms control.
- Replaced pronoun cadence with a neutral-to-personal sentence-subject scale from 0 to 5:
  - 0 keeps every sentence neutral or impersonal.
  - 1–4 assign exactly 20%, 40%, 60%, or 80% of final rows to randomly selected personal forms.
  - 5 changes the subject pattern on every consecutive row and includes neutral/impersonal
    structures in the rotation.
- Added a short contextual explanation that changes with the selected scale value.
- Applied the subject schedule to every final row, including extra-form rows.

## Capabilities retained from 0.4.0

- 5,000 ranked words for each of six languages, deterministic word selection, CEFR planning,
  question/statement allocation, and part-of-speech-aware extra forms.
- OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom-compatible providers.
- Resumable structured generation, Excel-safe XLSX/CSV, Edge neural TTS, partial MP3 recovery,
  safe local History, light/dark themes, Windows packaging, and bundled FFmpeg.

## Production release gate

The bundled production baseline contains exactly 5,000 validated, attributed wordfreq entries
for each of the six languages. Kaikki enrichment is reproducible and optional at runtime because
the generation provider supplies and validates missing translation/form evidence.

The CI release candidate performs silent install, launch, in-place upgrade/repair, bundled-file
verification, uninstall, and user-data preservation checks. Authenticode signing and verification
are automatically enabled when the protected signing-certificate secrets are configured. Public
release still requires a clean Windows 10/11 installer verification and publisher signing.
