# Specification traceability

This map is checked against both approved project artifacts at every build gate.

| Approved requirement | Implementation | Verification |
|---|---|---|
| Windows 10/11, Python 3.12, PySide6 | `pyproject.toml`, `ui/main_window.py` | Windows CI and packaged launch smoke test |
| Centered 50% launch; light/dark Power BI-inspired palette | `MainWindow.size_and_center()`, UI themes | Windows UI smoke test |
| Sentence Creation, Flashcards, TTS, History tabs | `MainWindow` | UI smoke test |
| OpenAI, Anthropic, Gemini, DeepSeek, Ollama, custom endpoint | `providers/` | provider contract tests |
| Session keys and Windows Credential Manager | `security/credentials.py` | platform-service and redaction tests |
| Dynamic base limit; forms 0–4; `base × (1 + forms) ≤ 5,000` | domain models and UI | boundary and UI tests |
| A1–C2, 5/8/11/14/17/20 words, contiguous gradual ranges | enums/models/validator | rule tests |
| Exact percentages and deterministic ascending allocation | planner/rules | allocation tests |
| Exact questions/statements and neutral-to-personal scale 0–5 | planner/rules | distribution and plan tests |
| LLM never selects frequency rank | frequency repository and plan | frequency tests |
| Source/licence data gate | JSONL schema and release tool | release-readiness gate |
| Seven-language/eight-option ingestion and automated validation | corpus build tools and word TSV | candidate and release-gate tests |
| Thai script and tone-marked Paiboon options | `Language`, Thai corpus builder, prompts | corpus, prompt, and UI tests |
| Targeted retries and resumable generation | service/checkpoints | integration tests |
| XLSX four public columns plus Metadata; legacy import | workbook service | round-trip tests |
| Header-free workbook rank: first data row is rank 1 | ranked workbook importer | workbook and flashcard integration tests |
| Words, Sentences, and combined flashcards | flashcard models/UI | domain and Windows UI tests |
| Inclusive rank filtering and no-repeat shuffle cycles | flashcard session model | permutation and boundary tests |
| Flashcard rows and study position persist across restarts | flashcard service and SQLite schema v2 | migration and resume integration tests |
| Unfocused controls pass wheel input to page scrolling | deliberate-wheel Qt controls | Windows wheel-interaction test |
| Edge TTS, dual voices, four pauses, 2-row preview | TTS service/UI | mocked integration tests |
| Pause/resume/cancel and checksum recovery | TTS manifests/service | recovery tests |
| Latest 20 files per type and safe app-owned actions | History service/UI | file-safety tests |
| Globe rising from an open book; native Windows identity | `assets/icons/logo.png`, `logo.ico`, AppUserModelID | packaging and Windows UI tests |
| Bundled runtime/FFmpeg and regular installer | Nuitka + Inno Setup | Windows workflow install/upgrade/uninstall acceptance |
| Authenticode publisher signing and provenance | signing script and Windows workflow | signature verification and build provenance artifact |
| README and example workbook included | README and `examples/` | packaging test |

## Phase status

- Phase 0 — repository and engineering foundation: complete
- Phase 1 — frequency schema, build pipeline, deterministic planning: complete;
  production corpus remains a public-release data gate
- Phase 2 — providers, credentials, discovery, and cost estimates: complete
- Phase 3 — generation, validation, checkpoints, and workbook output: complete
- Phase 4 — TTS and recovery: complete
- Phase 5 — History and local-file safety: complete
- Phase 6 — PySide6 interface: complete; Windows CI smoke test configured
- Phase 7 — standalone app and installer automation: complete; runs on Windows CI
- Phase 8 — automated hardening and production corpus: complete
- Phase 9 — clean Windows 10/11 client acceptance: complete
- Phase 10 — production 1.0.0 version alignment and tag-driven release automation:
  complete; Authenticode signing is applied when the protected publisher
  certificate secrets are configured
- Phase 11 — production 1.1.0 Thai expansion and Windows icon repair: complete;
  eight 5,000-entry language/script options and native executable/installer icons
- Phase 12 — v1.2.0 ranked flashcards and mouse-wheel input safety: implemented
  on an isolated release-candidate branch; Windows CI and explicit release approval
  are required before merge or publication
