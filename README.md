# Easy Language Learning Tool

> **Android companion in development:** The planned flashcard-only Android app will
> synchronize desktop-generated decks for offline study. See the
> [complete Android project plan and workflow](docs/ANDROID_PROJECT_PLAN.md).

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-v1.4.0-0078D4?logo=windows&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.0/EasyLanguageLearningTool-Setup-1.4.0.exe)
[![Download for Apple Silicon](https://img.shields.io/badge/macOS-Apple_Silicon-000000?logo=apple&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.0/EasyLanguageLearningTool-1.4.0-Apple-Silicon.dmg)
[![Download for Intel Mac](https://img.shields.io/badge/macOS-Intel-555555?logo=apple&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.0/EasyLanguageLearningTool-1.4.0-Intel.dmg)

**Windows users need the `.exe`; Mac users need the `.dmg` matching their processor.**
[Release notes, checksums, and build provenance](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/tag/v1.4.0)

> The installer is not yet Authenticode-signed, so Windows may display an Unknown Publisher or SmartScreen warning.
> The macOS apps are ad-hoc signed but not Apple-notarized, so Gatekeeper may require **Open** from the app's context menu on first launch.

Easy Language Learning Tool is a Windows and macOS desktop application for creating
structured language-learning sentence workbooks and turning those workbooks
into one natural-sounding, resumable MP3.

## What the application does

### Sentence Creation

- Supports US English, European Spanish, German, European Portuguese, French,
  Italian, and Thai. Thai is available as standard Thai script or tone-marked
  Paiboon romanization.
- Selects ranked words across all parts of speech deterministically from an internal
  dataset; the AI creates examples but never decides which words are most common.
- Connects to OpenAI, Anthropic, Google Gemini, DeepSeek, Ollama, or a custom
  OpenAI-compatible endpoint.
- Lets the user choose base words, a single CEFR level or a contiguous
  gradual A1–C2 range, exact level percentages, question percentage, and a
  neutral-to-personal sentence-subject scale. Scale 0 keeps every sentence neutral
  or impersonal; scales 1–4 use personal forms for 20%–80% of rows; scale 5 changes
  the subject pattern on every row.
- Allows 0–4 part-of-speech-aware extra forms and dynamically limits base words so
  `base words × (1 + extra forms)` never exceeds 5,000 final rows.
- Exports `.xlsx` with exactly four public columns on `Sentences` and a separate
  audit-ready `Metadata` sheet. Optional CSV export is supported by the core API.
- Checkpoints long AI jobs and retries only rejected or missing rows.

### Flashcards

- Loads an app-generated or schema-compatible `.xlsx` workbook without changing
  the source file.
- Studies Words, Sentences, or one combined card per row. Combined cards display
  the larger bold word above the sentence on the learning side and translation side.
- Uses a near-full-tab card with large uncluttered text, a compact language-pair
  badge, progress, and responsive light/dark styling.
- Loads from app History or Desktop and plays the visible word, sentence, or both.
  Matching TTS cell clips are reused; missing clips are generated on demand and cached.
- Ranks the first data row below the header as 1 and stores the ranked rows locally
  in SQLite.
- Supports an inclusive From rank / To rank filter through **Selected rows only**.
- Randomizes eligible rows without repetition until the selection is exhausted;
  Previous and Next preserve that order, while Shuffle again starts a new cycle.
- Restores the last workbook, display mode, selected ranks, shuffled order,
  position, and card side after restarting the app.

### Text to Speech

- Provides separate **Load from History** and **Load from Desktop** actions for
  app-owned or compatible `.xlsx` workbooks.
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
  moves deletions to the Windows Recycle Bin or macOS Trash.
- Never renames or deletes a file exported outside the app-owned History folder.

## End-user setup

1. Windows: run `EasyLanguageLearningTool-Setup-1.4.0.exe` and accept the default
   per-user installation folder and optional desktop shortcut.
2. macOS: open the DMG for your processor and drag **Easy Language Learning Tool**
   to **Applications**. On first launch, use **Open** from the context menu if
   Gatekeeper identifies the unnotarized build.
3. Launch the app. It opens centered at 50% of the screen; resize or maximize it normally.
4. In Sentence Creation, choose a provider:
   - Cloud: paste your own API key, test the connection, and select a model.
   - Local/free: install Ollama, run `ollama pull qwen3:8b`, then select Ollama and
     test `http://localhost:11434`.
5. Select languages and generation controls, choose a workbook location, and generate.
6. Open Flashcards to load a workbook, choose Words, Sentences, or both, optionally
   restrict the inclusive rank range, then flip and navigate the shuffled cards.
7. Open TTS, import a workbook, choose Language 1 for the foreign columns and
   Language 2 for the translation columns, preview two rows, then create the MP3.

The installed cloud-provider workflow requires no separate Python, Qt, FFmpeg,
or other runtime download. Ollama itself is optional and separately installed
only when the user chooses local generation.

API keys are session-only by default. **Remember securely** stores a key in the
current operating-system account's Credential Manager or macOS Keychain. Keys are never written to SQLite,
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
python tools\check_release_data.py resources\frequency_data\production\words.jsonl.gz
```

The automated corpus workflow uses `wordfreq` for six reproducible language
rankings. Thai uses the CC BY-SA OpenSubtitles ranking plus the CC0 Phupha 2026
frequency dataset, with Kaikki/Wiktionary validation and Paiboon romanization.
The three Thai lists proposed during development remain comparison sources only:
the Scribd list is all-rights-reserved, while the two public webpages do not grant
redistribution rights. Missing translations are generated and validated in
context. See `resources/frequency_data/README.md`.

## Windows build and installer

The Windows workflow runs all quality gates, downloads a pinned FFmpeg essentials
build, builds a standalone Qt application with Nuitka, compiles an Inno Setup
installer, performs silent install/launch/upgrade/uninstall acceptance testing,
and publishes the installer, portable directory, provenance record, and SHA-256
checksum. The same steps can be run locally by following
`.github/workflows/windows-build.yml`.

Public release maintainers can enable Authenticode signing by adding the protected
repository secrets `WINDOWS_SIGNING_CERTIFICATE_BASE64` (the Base64-encoded PFX)
and `WINDOWS_SIGNING_CERTIFICATE_PASSWORD`. Both must be configured together.
Pull-request builds remain deliberately unsigned; signed builds verify the
standalone executable and installer before artifact publication.

## macOS build and installer

The macOS workflow builds separate native application bundles and DMG installers
for Apple Silicon and Intel Macs. Each build bundles Python, Qt, application data,
FFmpeg, and FFprobe; validates the app bundle and architecture; runs a launch smoke
test; and publishes a SHA-256 checksum and provenance record. The apps are ad-hoc
signed. Apple Developer ID signing and notarization can be added when publisher
credentials are available.

## Data and release status

The repository includes exactly 5,000 ranked entries for each of eight language/
script options: six existing languages plus Thai script and Paiboon-romanized
Thai. Kaikki/Wiktionary enrichment tools
can add part-of-speech, form, and dictionary-translation evidence; when evidence
is unavailable, the generation model infers a valid grammatical use and supplies
the word translation. See `docs/RELEASE_READINESS.md`.

The interface caps the base-word control dynamically according to the available
corpus and selected extra forms, so it never accepts a job above 5,000 final rows.

Version 1.4.0 adds native Intel and Apple Silicon macOS packages while preserving
the complete Information guide, hardened flashcard audio, uniform card surface,
and mouse-wheel protections introduced in v1.3.0.

## Project documentation

- `resources/USER_MANUAL.md` is the offline guide shown by the Information tab.
- `docs/SPEC_TRACEABILITY.md` maps every approved requirement to code and tests.
- `docs/RELEASE_READINESS.md` defines automated and external release gates.
- Third-party notices are under `resources/licences` and `LICENSES`.

Never commit API keys or provider responses containing secrets.

---

# Complete User Manual

# 1. Sentence Creation

## 1.1 Connect an AI provider

Choose one of the following:

-  OpenAI 
-  Anthropic 
-  Google Gemini 
-  DeepSeek 
-  Ollama 
-  Custom OpenAI-compatible endpoint 

### Cloud providers

1.  Select the provider. 
2.  Paste your API key. 
3.  Optionally enable **Remember securely in Credential Manager or macOS Keychain**.
4.  Click **Test connection and load models**. 
5.  Select a model from the **Model** dropdown. 

API keys are not stored in workbooks, logs or the application database. If secure storage is disabled, the key lasts only for the current session.

### Ollama for local generation

1.  Install Ollama separately. 
2.  Download a model, for example: 

```
ollama pull qwen3:8b
```

3.  Start Ollama. 
4.  Select **Ollama** in the application. 
5.  Keep the default URL: 

```
http://localhost:11434
```

6.  Click **Test connection and load models**. 
7.  Select the downloaded model. 

Once Ollama and its model are installed, sentence generation can operate locally without sending prompts to a cloud AI provider.

### Custom endpoint

Select **Custom OpenAI-compatible**, enter the API key if required, and provide the complete base URL supplied by the service.

## 1.2 Select languages

- **Learning language:** Language being studied and used for the generated words and example sentences. 
- **Translation language:** Language used for word and sentence translations. 

Available options:

-  US English 
-  European Spanish 
-  German 
-  European Portuguese 
-  French 
-  Italian 
-  Thai (Thai script) 
-  Thai (Paiboon romanization) 

The two languages must be different.

Thai options:

- **Thai (Thai script):** Thai words and sentences use standard Thai characters. 
- **Thai (Paiboon romanization):** Thai is written using tone-marked Paiboon romanization. 

## 1.3 Choose the number of words

**Base words** determines how many ranked words are selected. Words are chosen by their internal frequency ranking; the AI does not choose which words are most common.

The application contains up to 5,000 ranked words for every language option.

## 1.4 Extra word forms

Each base word creates one original row. Extra forms create additional rows using grammatical variations where appropriate, such as:

-  Verb: `be → was` 
-  Noun: `tool → tools` 
-  Adjective: agreement or comparison 
-  Pronoun/determiner: agreement or case 
-  Invariant word: a different valid context 

The final workbook cannot exceed 5,000 rows.

| Extra forms | Rows per base word | Maximum base words |
|---:|---:|---:|
| 0 | 1 | 5,000 |
| 1 | 2 | 2,500 |
| 2 | 3 | 1,666 |
| 3 | 4 | 1,250 |
| 4 | 5 | 1,000 |

The **Calculated output** field updates automatically.

## 1.5 CEFR difficulty

### Single level

Select one level for every sentence:

| Level | Maximum sentence length |
|---|---:|
| A1 | 5 words |
| A2 | 8 words |
| B1 | 11 words |
| B2 | 14 words |
| C1 | 17 words |
| C2 | 20 words |

### Gradual increase

1.  Select **Gradual increase**. 
2.  Choose the starting and ending CEFR levels. 
3.  Assign percentages to the included levels. 
4.  Ensure **Percentage total** equals exactly `100%`. 

The workbook is arranged from easier to more advanced sentences.

## 1.6 Questions and statements

Use the **Questions / statements** slider to specify the percentage of questions.

Examples:

- `0%`: all statements 
- `20%`: 20% questions and 80% statements 
- `100%`: all questions 

Both open questions and yes/no questions may be generated.

## 1.7 Sentence-subject scale

This controls how often sentences use personal subjects.

| Option | Behaviour |
|---:|---|
| 0 | Every sentence stays neutral or impersonal. |
| 1 | 20% personal; 80% neutral. |
| 2 | 40% personal; 60% neutral. |
| 3 | 60% personal; 40% neutral. |
| 4 | 80% personal; 20% neutral. |
| 5 | Every consecutive sentence uses a different subject pattern. |

Neutral examples include:

-  The day is nice. 
-  The sun is up. 
-  The school is far. 

Personal patterns include first-, second- and third-person singular and plural forms. The explanation beneath the dropdown changes with the selected option.

## 1.8 Choose the output file

1.  Click **Browse** beside **Workbook**. 
2.  Select a folder and filename. 
3.  The application creates an `.xlsx` file. 

## 1.9 Cost estimate

The application shows estimated costs for different row counts and the current configuration.

These are estimates only. The AI provider’s billing information is authoritative. Pricing may appear as **Unknown** for unrecognized or newly released models.

## 1.10 Generate the workbook

The **Generate workbook** button becomes available when:

-  The provider is connected. 
-  A model is selected. 
-  The languages are different. 
-  The row limit is valid. 
-  Gradual CEFR percentages total 100%. 

Click **Generate workbook** and monitor the progress bar.

Long jobs use checkpoints. If generation fails, the application retains valid completed rows and can safely continue when the same settings, provider, model and output file are used again.

## 1.11 Workbook structure

The **Sentences** sheet contains:

1.  Foreign-language word 
2.  Word translation 
3.  Foreign-language sentence 
4.  Sentence translation 

The **Metadata** sheet records information including:

-  Row number 
-  Frequency rank 
-  CEFR level 
-  Part of speech 
-  Grammatical person 
-  Word form 
-  Question or statement 
-  Provider and model 
-  Validation result 
-  Token usage 
-  Estimated and actual cost 
-  Generation settings 

---

# 2. Flashcards

## 2.1 Load a workbook

Choose:

- **Load from History:** Select a workbook generated and retained by the application. 
- **Load from Desktop:** Select any compatible `.xlsx` workbook. 

The workbook is read-only; studying does not modify it.

## 2.2 Workbook requirements

A compatible workbook must contain no more than 5,000 rows and use these four headers:

```
Foreign-language word
Word translation
Foreign-language sentence
Sentence translation
```

Every used row must contain all four values.

## 2.3 Choose card content

Use the **Cards** dropdown:

- **Words:** Shows only the word and its translation. 
- **Sentences:** Shows only the sentence and its translation. 
- **Words and sentences:** Shows the word in larger bold text with the sentence underneath. 

Each workbook row creates one combined card.

## 2.4 Select rows by rank

The first data row below the workbook header is rank 1. Therefore:

-  Excel row 2 = rank 1 
-  Excel row 6 = rank 5 

To study a specific range:

1.  Enable **Selected rows only**. 
2.  Enter an inclusive **From** rank. 
3.  Enter an inclusive **To** rank. 
4.  Click **Apply rows**. 

For example, `100` to `300` studies 201 cards.

Disable **Selected rows only** to use the complete workbook.

## 2.5 Study cards

-  The front shows the learning-language content. 
-  Click the card or **Reveal** to show the translation. 
-  Click **Show learning side** to return to the front. 
-  Use **Previous** and **Next** to navigate. 
-  Use **Reshuffle** to create a new random order. 

Every eligible card appears once before any card repeats. Previous and Next preserve the current shuffled sequence.

The application restores the last workbook, range, card order, position and visible side after restarting.

## 2.6 Flashcard sound

Click the speaker button to read the currently visible side.

- **Words mode:** Reads the word. 
- **Sentences mode:** Reads the sentence. 
- **Combined mode:** Reads the word and then the sentence. 
-  The button can be pressed repeatedly on either side. 

The first playback may take several seconds because missing audio is generated using Microsoft Edge neural TTS. Generated audio is cached, making subsequent playback faster and allowing cached cards to play offline.

An internet connection is required when a card’s audio has not previously been generated.

---

# 3. Text to Speech

## 3.1 Load a workbook

Use:

- **Load from History** 
- **Load from Desktop** 

Only compatible four-column `.xlsx` workbooks are accepted.

## 3.2 Set languages correctly

- **Language 1 — foreign columns:** Must match workbook columns 1 and 3. 
- **Language 2 — translation columns:** Must match workbook columns 2 and 4. 

The TTS language selections are not automatically changed when loading an external workbook, so verify them before generating audio.

## 3.3 Select voices

Choose separate voices for:

-  Foreign words and sentences 
-  Word and sentence translations 

Click **Refresh available Edge voices** to retrieve the current voice list. This requires internet access.

## 3.4 Adjust speech

Each language has separate settings:

- **Speed:** `-100%` to `+100%` 
- **Pitch:** `-100 Hz` to `+100 Hz` 
- **Volume:** `-100%` to `+100%` 

A value of `0` uses the normal voice setting.

## 3.5 Set break durations

Four pauses can be set from 1 to 10 seconds:

1.  Foreign word → word translation 
2.  Word translation → foreign sentence 
3.  Foreign sentence → sentence translation 
4.  Sentence translation → next row 

## 3.6 Preview

Click **Preview 2 rows**.

The app generates audio for exactly the first two workbook rows and opens the preview in the default system audio player.

## 3.7 Create the complete MP3

1.  Click **Create MP3**. 
2.  Choose the output location. 
3.  Monitor the progress bar. 

The final order for every row is:

1.  Foreign word 
2.  Word translation 
3.  Foreign sentence 
4.  Sentence translation 

## 3.8 Pause, resume and cancel

- **Pause:** Pauses the active generation job. 
- **Resume:** Continues a paused job. 
- **Cancel:** Stops the job safely. 

Completed rows are retained. If a job is cancelled or fails, a partial MP3 is added to History.

To continue:

1.  Load the same workbook. 
2.  Keep the same languages, voices and audio settings. 
3.  Click **Create MP3** again. 

The application validates workbook and setting checksums before resuming.

---

# 4. History

History stores:

-  The latest 20 app-owned workbooks 
-  The latest 20 app-owned audio files 

Files are stored under:

```
Documents\Easy Language Learning Tool\History
```

Select one row before using an action.

## History actions

- **Refresh:** Reload the list. 
- **Use in Flashcards:** Opens a selected workbook in Flashcards. 
- **Use in TTS:** Opens a selected workbook in TTS. 
- **Rename:** Renames the app-owned History file. 
- **Delete to Recycle Bin / Trash:** Removes the app-owned copy safely.
- **Re-export:** Copies the file to another location. 
- **Regenerate:** Restores the original workbook-generation settings. 

Regenerate does not overwrite the original. It creates a new output path and uses a new random seed. Reconnect the AI provider before generating.

Files exported outside History are not renamed or deleted when their History copies are changed.

When more than 20 files of one type exist, the oldest app-owned items are moved to the Recycle Bin or Trash.

---

# 5. Offline and internet requirements

| Feature | Internet required? |
|---|:---:|
| Open existing workbooks | No |
| Study text flashcards | No |
| Play previously cached flashcard audio | No |
| Generate new flashcard audio | Yes |
| Cloud AI sentence generation | Yes |
| Ollama generation after model installation | No |
| Refresh Edge voices | Yes |
| Generate TTS audio | Yes |
| History management | No |

Cloud generation sends the necessary prompt content to the selected AI provider. Edge TTS sends the text required for speech synthesis to Microsoft’s service.

---

# 6. Common problems

## Generate workbook is disabled

Check that:

-  The provider connection succeeded. 
-  A model is selected. 
-  Learning and translation languages differ. 
-  The final row count is at most 5,000. 
-  Gradual CEFR percentages equal 100%. 
-  The output path is valid. 

## Provider connection fails

Check:

-  API key accuracy 
-  Provider billing or credits 
-  Internet connection 
-  Custom endpoint URL 
-  Ollama is running 
-  Selected Ollama model has been downloaded 

## Workbook is rejected

Confirm:

-  The file is `.xlsx`. 
-  It contains the required four headers. 
-  Every data row has all four cells. 
-  It has no more than 5,000 data rows. 

## Flashcard audio does not play

-  Wait for the first on-demand generation. 
-  Confirm internet access for uncached cards. 
-  Check system volume and output-device settings.
-  Try the speaker button again; repeated playback is supported. 
-  Confirm the workbook cells contain valid text. 

## TTS job stops

The completed portion is preserved. Keep the same workbook and settings, then run **Create MP3** again to resume safely.
