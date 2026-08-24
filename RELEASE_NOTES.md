# Easy Language Learning Tool 0.4.0 — all-word internal release candidate

## Changed

- Expanded generation from verbs to the 5,000 most common words across all parts of speech.
- Added Italian throughout language selection, corpus models, voices, tests, and documentation.
- Replaced the former 4,000-base/1,000-extra-form rule with a universal 5,000-final-row formula: `base words × (1 + extra forms) ≤ 5,000`.
- Added a clear row-limit explanation above Sentence Creation controls and a dynamic base maximum.
- Generalized extra forms for verbs, nouns, adjectives, pronouns/determiners, and invariant words.
- Updated workbook headers to `Foreign-language word` and `Word translation`; previous verb headers remain import-compatible.
- Replaced the human-review corpus gate with reproducible wordfreq ranking, Kaikki/Wiktionary enrichment, automated validation, and cross-source comparison.

## Existing capabilities retained

- OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom-compatible providers.
- Deterministic CEFR, question/statement, pronoun, frequency-rank, and extra-form planning.
- Resumable structured generation, Excel-safe XLSX/CSV, Edge neural TTS, partial MP3 recovery, and safe local History.
- PySide6 light/dark interface, centered 50% launch, Windows installer automation, bundled FFmpeg, and security/testing gates.

## Production release gate

The bundled production baseline contains exactly 5,000 validated, attributed wordfreq entries for each of the six languages. Public release still requires clean Windows 10/11 installer verification and publisher signing. Kaikki enrichment is reproducible and optional at runtime because the generation provider supplies and validates missing translation/form evidence.
