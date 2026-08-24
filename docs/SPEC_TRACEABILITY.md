# Specification traceability

This map is checked against both approved project artifacts at every build gate.

| Approved requirement | Implementation | Verification |
|---|---|---|
| Windows 10/11, Python 3.12, PySide6 | `pyproject.toml`, `ui/main_window.py` | Windows CI and packaged launch smoke test |
| Centered 50% launch; light/dark Power BI-inspired palette | `MainWindow.size_and_center()`, UI themes | Windows UI smoke test |
| Sentence Creation, TTS, History tabs | `MainWindow` | UI smoke test |
| OpenAI, Anthropic, Gemini, DeepSeek, Ollama, custom endpoint | `providers/` | provider contract tests |
| Session keys and Windows Credential Manager | `security/credentials.py` | platform-service and redaction tests |
| Dynamic base limit; forms 0–4; `base × (1 + forms) ≤ 5,000` | domain models and UI | boundary and UI tests |
| A1–C2, 5/8/11/14/17/20 words, contiguous gradual ranges | enums/models/validator | rule tests |
| Exact percentages and deterministic ascending allocation | planner/rules | allocation tests |
| Exact questions/statements and pronoun cadence 1–5 | planner/rules | plan tests |
| LLM never selects frequency rank | frequency repository and plan | frequency tests |
| Source/licence data gate | JSONL schema and release tool | release-readiness gate |
| Six-language all-word ingestion and automated validation | corpus build tools and word TSV | candidate and release-gate tests |
| Targeted retries and resumable generation | service/checkpoints | integration tests |
| XLSX four public columns plus Metadata; legacy import | workbook service | round-trip tests |
| Edge TTS, dual voices, four pauses, 2-row preview | TTS service/UI | mocked integration tests |
| Pause/resume/cancel and checksum recovery | TTS manifests/service | recovery tests |
| Latest 20 files per type and safe app-owned actions | History service/UI | file-safety tests |
| World-map/letters logo | `assets/icons/logo.svg` | packaging test |
| Bundled runtime/FFmpeg and regular installer | Nuitka + Inno Setup | Windows workflow |
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
- Phase 8 — automated hardening complete; publisher signing and the production
  frequency corpus are external public-release gates
