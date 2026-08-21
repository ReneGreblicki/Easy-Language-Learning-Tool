# Easy Language Learning Tool

## Development Workflow and Test Plan

Version: 1.0  
Target platform: Windows 10/11, 64-bit  
Distribution: Regular Windows installer, free distribution  
Application language: US English

## 1. Locked product rules

### Supported languages

- US English
- European Spanish
- German
- European Portuguese
- French

Generated language should use the standard national form used in education and professional settings. Dialect, slang, internet shorthand, and unnecessary contractions should be minimized.

### AI providers

Initial providers:

- OpenAI
- Anthropic
- Google Gemini
- DeepSeek
- Ollama
- Custom OpenAI-compatible endpoint

Users select a provider, enter their own API key where required, test the connection, and then select an available model. Keys are stored only through Windows Credential Manager when the user selects **Remember key**. Keys must never be stored in SQLite, logs, workbooks, crash reports, or exported configuration.

If no cloud API is configured, the application checks for Ollama at `http://localhost:11434`. Installation and model guidance appears under **Show more**.

### Generation limits

- Base-sentence count: any whole number from 1 to 4,000.
- The cost panel always includes comparison estimates for 1,000, 2,000, 3,000, and 4,000 base sentences, plus the user's current configuration.
- Extra verb forms: 0–4.
- The extra-form control is enabled only when base sentences are 1,000 or fewer.
- Final output is hard-limited to 5,000 rows.
- Formula: `final_rows = base_sentences × (1 + extra_forms)`.
- The Generate button remains disabled when any configuration would exceed the limit.

### CEFR rules

| Level | Maximum sentence length |
|---|---:|
| A1 | 5 words |
| A2 | 8 words |
| B1 | 11 words |
| B2 | 14 words |
| C1 | 17 words |
| C2 | 20 words |

- Single-level and gradual modes are supported.
- Gradual ranges must be contiguous and ordered `A1 → A2 → B1 → B2 → C1 → C2`.
- Percentages must total exactly 100%.
- Row counts are allocated with deterministic largest-remainder rounding.
- Rows are ordered from the lowest selected CEFR level to the highest.
- Vocabulary outside the assigned level is minimized rather than prohibited.
- Vocabulary, grammar, and sentence length are all controlled by CEFR level.
- Translations prioritize accuracy and directness without losing meaning.

### Sentence composition

- The application selects verbs deterministically from internal frequency data.
- Base verbs do not repeat until the verified list is exhausted.
- After exhaustion, the engine continues into lower-confidence verified verbs.
- Questions and declarative statements follow the exact requested allocation after deterministic rounding.
- Both yes/no and open questions are allowed.
- Every sentence must use the selected verb.
- Every sentence must be complete, independently understandable, and grammatically coherent.
- Extra-form rows use the same lemma but a different valid tense, mood, or construction.
- Extra forms inherit the CEFR level of their base sentence.

### Pronoun-change scale

| Value | Behaviour |
|---:|---|
| 1 | One randomly selected grammatical person for the entire job |
| 2 | Change every 20 base sentences |
| 3 | Change every 10 base sentences |
| 4 | Change every 3 base sentences |
| 5 | Change every base sentence |

Whenever a change is due, the next grammatical person must differ from the immediately previous one.

### Workbook output

Canonical format: `.xlsx`  
Optional format: `.csv`

The `Sentences` sheet contains exactly:

1. Foreign-language verb
2. Verb translation
3. Foreign-language sentence
4. Sentence translation

The `Metadata` sheet records:

- CEFR level
- Frequency rank
- Grammatical person
- Tense or form
- Question or statement
- Generation timestamp
- Provider and model
- Validation status
- Random seed
- Generation settings
- Input/output token usage
- Estimated and actual API cost where available

### TTS rules

- Input comes from History or a user-selected `.xlsx` file.
- Imported workbooks must match the required four-column schema.
- Output is one combined MP3.
- Spoken sequence: foreign verb, verb translation, foreign sentence, sentence translation.
- Foreign columns use the foreign-language voice; translation columns use the translation-language voice.
- Each language has voice, speed, pitch, and volume controls.
- Four pause sliders cover all transitions, including the pause before the next row.
- Pause range: 1–10 seconds.
- Preview synthesizes exactly two rows.
- Start, pause, resume, and cancel are supported.
- No row repetition.
- Partial MP3 and completed clips are preserved after failure or cancellation.
- Resume requires a matching workbook checksum and matching TTS settings.

### History rules

- Keep the latest 20 spreadsheets and latest 20 audio files.
- When a 21st app-owned file is created, move the oldest matching file to the Windows Recycle Bin.
- Rename affects the app-owned file and metadata only.
- Delete affects app-owned files only and uses the Recycle Bin.
- Export creates an external copy that the app never renames or deletes.
- Regenerate keeps the original, reuses saved settings, creates a new seed, and creates a separate output.

### Window and visual rules

- Application launches at 50% of the available screen size.
- The initial window is centered and keeps the designed aspect ratio.
- Users can resize or maximize it normally.
- Light and dark themes use a Power BI-inspired blue palette.
- The application contains Sentence Creation, TTS, and History tabs.
- Branding uses a world map with multilingual letters emerging from it.

## 2. Repository structure

```text
easy-language-learning-tool/
├── pyproject.toml
├── README.md
├── LICENSES/
├── assets/
│   ├── icons/
│   └── themes/
├── installer/
│   ├── inno_setup.iss
│   └── bundled/
│       └── ffmpeg/
├── resources/
│   ├── frequency_data/
│   ├── licences/
│   └── pricing/
├── src/easy_language_learning_tool/
│   ├── app.py
│   ├── config/
│   ├── domain/
│   ├── generation/
│   ├── providers/
│   ├── validation/
│   ├── tts/
│   ├── history/
│   ├── persistence/
│   └── ui/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── ui/
│   ├── e2e/
│   ├── packaging/
│   ├── fixtures/
│   └── golden/
└── .github/workflows/
    ├── quality.yml
    ├── tests.yml
    ├── windows-build.yml
    └── release.yml
```

## 3. Branch and issue workflow

1. `main` always contains a releasable version.
2. Every change is developed in a short feature or fix branch.
3. Every branch is linked to a GitHub issue with acceptance criteria.
4. Pull requests require automated checks and a concise manual verification note.
5. No feature is merged with failing tests, unresolved high-severity defects, or unreviewed dependency/licence changes.
6. Releases use semantic versions and signed Git tags where available.

Suggested issue labels:

- `feature`
- `bug`
- `data-quality`
- `linguistic-review`
- `provider`
- `tts`
- `ui`
- `installer`
- `security`
- `testing`
- `release-blocker`

## 4. Development phases and quality gates

### Phase 0 — Repository and engineering foundation

Deliverables:

- Python project and dependency lock file
- PySide6 application shell
- Configuration and structured logging
- SQLite migration framework
- Ruff, mypy, pytest, pre-commit
- GitHub Actions workflows
- Windows build job
- Licence inventory

Gate:

- Clean installation into a new virtual environment.
- Empty application launches at 50% screen size.
- Ruff, mypy, unit tests, and dependency audit pass.
- No secrets appear in the repository.

### Phase 1 — Frequency data and deterministic planning

Deliverables:

- Licensed frequency lists for all five languages
- Lemma normalization, POS filtering, duplicate removal, and exclusions
- Attribution and licence files
- Deterministic verb selector
- CEFR allocator
- question/statement allocator
- pronoun schedule
- form-count guardrails

Gate:

- No duplicate lemma before list exhaustion.
- Same seed and configuration produce the same plan.
- All CEFR and sentence-type allocations reconcile exactly to final row count.
- All five language datasets pass schema and licence checks.

### Phase 2 — Provider framework and cost estimation

Deliverables:

- OpenAI, Anthropic, Gemini, DeepSeek, Ollama, and custom-compatible adapters
- Connection tests and model discovery
- Windows Credential Manager integration
- Pricing registry with source and last-updated date
- Pre-generation estimates and post-generation actual usage
- Standardized retry, timeout, authentication, and rate-limit handling

Gate:

- Provider contract suite passes for every adapter.
- Invalid credentials produce a clear, non-destructive error.
- Keys do not appear in logs, SQLite, exported files, or process diagnostics.
- Unknown pricing is displayed as `Unknown`.
- Ollama fallback works without a cloud API key.

### Phase 3 — Sentence generation and linguistic validation

Deliverables:

- Batched structured generation
- Checkpointing and resume
- Validation pipeline
- Targeted row retry
- Workbook and CSV export
- Metadata sheet

Gate:

- 100% of accepted rows match the schema.
- 100% contain the assigned verb or a valid inflection.
- 100% obey the assigned word-count maximum.
- Requested question ratio and CEFR allocation reconcile exactly.
- Duplicate base verbs are absent before frequency-list exhaustion.
- Interrupted jobs resume without losing or duplicating accepted rows.
- Golden linguistic suite meets the agreed manual-review threshold.

### Phase 4 — TTS engine and recovery

Deliverables:

- Dynamic Edge voice discovery and locale filtering
- Voice, speed, pitch, and volume controls
- Two-row preview
- Cell clips, row clips, silence clips, and combined MP3
- Pause, resume, cancel, retry, partial export, and continuation
- Workbook/configuration checksum protection
- Duration and file-size warning

Gate:

- Four columns are spoken in the correct language/voice order.
- Each configured pause is within tolerance.
- Cancel and simulated failure preserve the correct last completed row.
- Resume neither repeats nor skips a row.
- Final output passes FFmpeg decoding and metadata checks.

### Phase 5 — History and local-file safety

Deliverables:

- SQLite history catalogue
- Rename, delete, re-export, and regenerate
- 20-file retention per type
- Recycle Bin integration
- External-export isolation

Gate:

- Creating item 21 moves only the oldest app-owned matching file to Recycle Bin.
- Deleting or renaming never changes an exported external copy.
- Missing or manually moved history files are reported without crashing.
- Database and filesystem remain consistent after forced shutdown.

### Phase 6 — Complete PySide6 interface

Deliverables:

- Three finished tabs
- API/model setup and Show more guidance
- Light/dark themes
- progress, validation, warning, error, and recovery states
- keyboard navigation and accessible labels
- logo and Windows icons

Gate:

- UI tests cover every form constraint and primary action.
- All controls remain readable at 100%, 125%, 150%, and 200% Windows scaling.
- Launch size is approximately 50% of available screen dimensions and centered.
- No long-running job blocks the UI thread.

### Phase 7 — Installer and offline dependency packaging

Deliverables:

- Nuitka/PySide6 executable
- Inno Setup installer and uninstaller
- Bundled FFmpeg binaries and required notices
- Bundled Python/Qt runtime and application data
- Start menu and optional desktop shortcuts
- `README.md` with setup, API, Ollama, use, recovery, privacy, and troubleshooting instructions
- Third-party licence directory

Gate:

- Clean Windows VM can install and run the normal cloud-API workflow without Python, FFmpeg, or other runtime downloads.
- Installer, repair/reinstall, upgrade, and uninstall tests pass.
- Uninstall does not remove user exports.
- Optional Ollama remains a separate user installation because of its hardware-dependent, multi-gigabyte runtime and model files; the README and Show more panel provide instructions.

### Phase 8 — Release hardening

Deliverables:

- Full regression run
- Five-language linguistic review
- provider smoke tests
- long-generation and long-audio soak tests
- Windows Defender scan
- release notes, checksums, and known limitations

Gate:

- No open critical or high-severity defects.
- No failed required test.
- All release acceptance scenarios pass on a clean Windows machine.
- README instructions are followed successfully by a tester who did not build the app.

## 5. Test strategy

### Automated test levels

| Level | Purpose | Runs |
|---|---|---|
| Unit | Pure rules, calculations, validation, paths, metadata | Every commit |
| Contract | Consistent behaviour across AI provider adapters | Every pull request |
| Integration | SQLite, files, Excel, credentials, FFmpeg, mocked TTS/API | Every pull request |
| UI | Widgets, validation, themes, navigation, worker signalling | Every pull request |
| End-to-end | Full generation and TTS scenarios with controlled fixtures | Nightly and release |
| Packaging | Executable, installer, upgrade, uninstall | Release candidate |
| Linguistic | CEFR, grammar, translation, form and naturalness review | Milestones and release |
| Performance | Memory, runtime, responsiveness, large jobs | Nightly and release |
| Security | secret leakage, path traversal, malformed files, dependency audit | Every pull request and release |

### Core unit tests

#### Row-limit tests

- `1000 × (1 + 0) = 1000` accepted.
- `1000 × (1 + 4) = 5000` accepted.
- Extra-form dropdown enabled for every base count from 1 through 1,000.
- Extra-form dropdown hidden or disabled for every base count from 1,001 through 4,000.
- Any calculated result over 5,000 is rejected at domain and UI layers.
- An imported workbook over 5,000 rows is rejected for TTS with a clear explanation of the application limit.

#### CEFR allocation tests

- Percentages other than 100% are rejected.
- Non-contiguous ranges are rejected.
- Largest-remainder allocation always equals the requested base count.
- Ties are resolved predictably by CEFR order.
- Output blocks remain in ascending CEFR order.

#### Pronoun tests

- Level 1 never changes person.
- Levels 2–5 change at exactly the required boundaries.
- A scheduled change never selects the immediately previous person.
- Pro-drop languages track grammatical person even when no written pronoun is required.

#### Sentence-type tests

- Question and statement totals exactly match deterministic allocation.
- Questions end with language-appropriate question punctuation.
- Both open and yes/no questions appear in a sufficiently large generated set.

#### Workbook tests

- Required headers are exact and ordered.
- Missing, duplicated, renamed, or additional required columns are reported clearly.
- Formula cells, macros, malformed XML, and oversized content are handled safely.
- CSV UTF-8 round-trip preserves accents and punctuation.
- Metadata counts reconcile to the Sentences sheet.

### Provider contract tests

Every provider adapter must pass the same suite:

- Validate or reject credentials.
- Discover models, or clearly state when discovery is unsupported.
- Generate structured rows from a fixed request.
- Report token usage where available.
- Map authentication, timeout, rate limit, malformed response, and server errors into common application errors.
- Support cancellation between batches.
- Never expose the full key in exceptions or logs.
- Return `Unknown` when pricing data is missing.

Network calls are mocked in normal CI. A minimal live smoke suite runs manually or in a protected release environment using dedicated low-limit test keys.

### Linguistic quality tests

Create a golden review set containing at least 10 examples for each language × CEFR combination: `5 × 6 × 10 = 300` manually reviewed cases.

Each reviewed row scores:

- Correct language
- Correct lemma and inflection
- Grammatical correctness
- Standalone comprehensibility
- CEFR-appropriate vocabulary
- CEFR-appropriate grammar
- Word-count compliance
- Translation accuracy
- Translation directness
- Formal/standard register
- Question/statement correctness
- Naturalness

Release threshold:

- Zero structural or word-count failures.
- At least 95% acceptable for grammar, meaning, verb use, and translation.
- At least 90% acceptable for CEFR fit and naturalness.
- All critical linguistic errors corrected or added to retry/exclusion rules.

### TTS tests

- Mock Edge synthesis for deterministic CI.
- Run a small live two-row preview smoke test before release.
- Verify MP3 codec and decodeability with `ffprobe`/FFmpeg.
- Verify spoken clip order from the manifest.
- Verify pause duration within ±100 ms per transition before final encoding.
- Verify voice locale matches the assigned column language.
- Verify speed, pitch, and volume parameters reach the synthesis/audio-processing layer.
- Interrupt at the first row, a middle row, and the final row; verify correct recovery metadata.
- Modify the workbook after interruption; verify unsafe resume is blocked.
- Modify TTS settings after interruption; verify resume creates a new job or requests confirmation.
- Verify partial MP3 export remains playable.
- Run long-audio soak tests without requiring a live network by using prepared fixture clips.

### History and destructive-action tests

- Retention is independent for spreadsheets and MP3 files.
- The 21st file moves the oldest app-owned file to Recycle Bin.
- Symlinks, junctions, `..` paths, and external paths cannot escape the app-owned history directory.
- Rename collision produces a safe prompt and never overwrites silently.
- Export collision uses explicit overwrite confirmation or a unique filename.
- Database rollback occurs if a filesystem mutation fails.
- Filesystem rollback or repair occurs if the database update fails.

### UI tests

- Launch at 50% screen size on common screen resolutions.
- Centering and minimum size remain valid on multi-monitor configurations.
- Extra forms react immediately to base-count selection.
- CEFR percentage controls cannot leave the form in a silently invalid state.
- Generate remains disabled until all required inputs are valid.
- Long tasks keep the interface responsive.
- Pause, resume, and cancel state transitions expose only valid actions.
- Light/dark themes cover normal, hover, focused, disabled, warning, and error states.
- Keyboard-only navigation follows a logical order.
- Labels and status changes are exposed to Windows accessibility APIs where Qt supports them.

### Performance tests

Targets on the documented minimum supported machine:

- Cold launch to interactive UI: ≤5 seconds.
- UI actions without network work: perceived response ≤200 ms.
- Workbook import of 5,000 rows: ≤3 seconds under typical conditions.
- Peak memory during 5,000-row workbook handling: ≤750 MB.
- Generation and TTS must stream/checkpoint rather than retain all audio bytes in memory.
- History load with 40 retained files: ≤1 second.
- UI thread must not contain blocking network, file-conversion, or FFmpeg work.

### Installer tests

Test on clean Windows 10 and Windows 11 VMs:

- Fresh install
- Launch from Start menu
- Optional desktop shortcut
- Normal user permissions
- Path containing spaces and non-ASCII characters
- FFmpeg works without separate installation
- Python and Qt runtimes require no separate installation
- Upgrade from previous version preserves history and settings
- Repair/reinstall behaviour
- Uninstall removes program files but preserves user exports
- Reboot is not required unless Windows itself locks a replaced file
- README is installed and accessible from the Start menu/app Help menu

## 6. CI workflow

### `quality.yml`

Runs on every pull request:

- Ruff formatting and linting
- mypy
- dependency vulnerability audit
- secret scan
- licence inventory check

### `tests.yml`

Runs on every pull request:

- unit tests
- provider contract tests with mocks
- integration tests
- PySide6 headless UI tests
- coverage report

Required initial coverage:

- Overall line coverage: at least 85%
- Domain rules, allocation, row limits, recovery, path safety, and credential redaction: at least 95%
- Coverage is a floor, not a substitute for behavioural assertions.

### `windows-build.yml`

Runs on release candidates and optionally nightly:

- Build Windows executable
- Build Inno Setup installer
- Launch executable smoke test
- Inspect bundled files and licences
- Upload installer and checksum as CI artifacts

### `release.yml`

Runs only after an approved version tag:

- Repeat required checks
- Build final installer
- Generate SHA-256 checksum
- Attach README, release notes, licence bundle, and installer
- Preserve test report and build provenance

## 7. Test data and environments

- Never use personal production API keys in CI.
- Use dedicated restricted test keys only for protected live smoke tests.
- Use mocked provider responses for normal automated testing.
- Keep deterministic fixture workbooks for 0, 1, 2, 999, 1,000, and 5,000 rows.
- Include malformed, empty, wrong-language, duplicate, oversized, and interrupted-job fixtures.
- Preserve the supplied German workbook and audio as reference material, not as pass/fail truth.
- Store approved golden linguistic samples with reviewer status and version history.

## 8. Definition of done for every feature

A feature is complete only when:

1. Acceptance criteria are implemented.
2. Unit/integration/UI tests appropriate to the change are added.
3. Existing required tests pass.
4. Error, cancellation, and recovery paths are tested.
5. No secret or destructive file-safety regression is introduced.
6. User-facing text and README content are updated when behaviour changes.
7. Third-party licences and notices are updated when dependencies or data change.
8. The feature is manually verified in the packaged Windows application when packaging could affect it.

## 9. Release acceptance checklist

- [ ] All five languages pass dataset validation.
- [ ] All provider adapters pass contract tests.
- [ ] DeepSeek appears in provider selection and completes a smoke generation.
- [ ] No configuration can exceed 5,000 final rows.
- [ ] Extra forms appear only for base counts of 1,000 or fewer.
- [ ] CEFR, question, pronoun, verb, and sentence-length rules pass.
- [ ] Workbook and CSV exports open correctly.
- [ ] TTS preview, full generation, interruption, partial export, and resume pass.
- [ ] History retention and Recycle Bin tests pass.
- [ ] App launches centered at 50% screen size.
- [ ] Light and dark themes pass visual inspection.
- [ ] Clean Windows installation requires no separate Python, Qt, or FFmpeg download.
- [ ] README setup instructions are verified by a new tester.
- [ ] Optional Ollama instructions are current and clearly separated from required setup.
- [ ] Third-party licences and source attributions are included.
- [ ] No critical/high defects remain open.
- [ ] Installer and SHA-256 checksum are produced.
