# Easy Language Learning Tool

Easy Language Learning Tool is a Windows desktop application for creating
structured language-learning sentence workbooks and turning those workbooks
into one natural-sounding, resumable MP3.

## What the application does

### Sentence Creation

- Supports US English, European Spanish, German, European Portuguese, and French.
- Selects unique verbs deterministically from an internal ranked dataset; the AI
  model creates examples but never decides which verbs are most common.
- Connects to OpenAI, Anthropic, Google Gemini, DeepSeek, Ollama, or a custom
  OpenAI-compatible endpoint.
- Lets the user choose 1–4,000 base sentences, a single CEFR level or a contiguous
  gradual A1–C2 range, exact level percentages, question percentage, and pronoun
  cadence.
- Allows 0–4 extra forms only at 1,000 or fewer base sentences and never permits
  more than 5,000 final rows.
- Exports `.xlsx` with exactly four public columns on `Sentences` and a separate
  audit-ready `Metadata` sheet. Optional CSV export is supported by the core API.
- Checkpoints long AI jobs and retries only rejected or missing rows.

### Text to Speech

- Imports an app History workbook or any compatible `.xlsx` file.
- Uses Microsoft Edge neural voices for the foreign columns and a separate voice
  for the translation columns.
- Supports voice, speed, pitch, volume, and four 1–10 second break controls.
- Previews exactly two rows, or creates one combined MP3.
- Supports pause, resume, and cancel. A failed or cancelled job preserves its last
  completed row and partial MP3, and safely resumes only when checksums match.
- Uses bundled `ffmpeg.exe` and `ffprobe.exe` in the Windows installer.

### History

- Retains the latest 20 app-owned spreadsheets and 20 app-owned MP3 files.
- Renames app-owned files, exports safe copies, restores generation settings, and
  moves deletions to the Windows Recycle Bin.
- Never renames or deletes a file exported outside the app-owned History folder.

## End-user setup

1. Run `EasyLanguageLearningTool-Setup-0.2.1.exe`.
2. Accept the default per-user installation folder and optional desktop shortcut.
3. Launch the app. It opens centered at 50% of the screen; resize or maximize it normally.
4. In Sentence Creation, choose a provider:
   - Cloud: paste your own API key, test the connection, and select a model.
   - Local/free: install Ollama, run `ollama pull qwen3:8b`, then select Ollama and
     test `http://localhost:11434`.
5. Select languages and generation controls, choose a workbook location, and generate.
6. Open TTS, import a workbook, choose Language 1 for the foreign columns and
   Language 2 for the translation columns, preview two rows, then create the MP3.

The installed cloud-provider workflow requires no separate Python, Qt, FFmpeg,
or other runtime download. Ollama itself is optional and separately installed
only when the user chooses local generation.

API keys are session-only by default. **Remember securely** stores a key in the
current Windows account's Credential Manager. Keys are never written to SQLite,
logs, workbooks, checkpoints, or exported settings.

## Example workbook

`examples/Expected_Workbook_Format.xlsx` is the canonical import/export example.
Imported workbooks must use its four `Sentences` headers and contain no empty
required cells. The supplied legacy German workbook headers are also accepted.

## Developer setup

Requirements: 64-bit Python 3.12 and Git. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
easy-language-learning-tool
```

Quality checks:

```powershell
ruff format --check .
ruff check .
mypy src
pytest --cov=easy_language_learning_tool --cov-report=term-missing --cov-fail-under=85
```

Frequency-data build and gate:

```powershell
python -m pip install -e ".[data-build]"
python tools\build_frequency_data.py --help
python tools\check_release_data.py resources\frequency_data\production\verbs.jsonl
```

## Windows build and installer

The Windows workflow runs all quality gates, downloads a pinned FFmpeg essentials
build, builds a standalone Qt application with Nuitka, compiles an Inno Setup
installer, and publishes the installer, portable directory, and SHA-256 checksum.
The same steps can be run locally by following `.github/workflows/windows-build.yml`.

## Data and release status

The application architecture and demo corpus are ready for development and
internal testing. A public installer is blocked until the reviewed frequency
dataset reaches at least 4,000 unique, attributed verb lemmas for every supported
language. See `docs/RELEASE_READINESS.md`. This prevents demo or licence-unclear
material from being presented as production frequency data.

## Project documentation

- `docs/SPEC_TRACEABILITY.md` maps every approved requirement to code and tests.
- `docs/RELEASE_READINESS.md` defines automated and external release gates.
- Third-party notices are under `resources/licences` and `LICENSES`.

Never commit API keys or provider responses containing secrets.
