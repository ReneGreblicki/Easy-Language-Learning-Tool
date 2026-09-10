# Easy Language Learning Tool

> **Mobile companion:** The Android app synchronizes desktop-generated decks for
> offline study. The iOS adaptation is paused for a future release. See the
> [mobile project plan](docs/ANDROID_PROJECT_PLAN.md) and
> [Apple platform plan](docs/APPLE_PLATFORM_PLAN.md).

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-v1.4.1-0078D4?logo=windows&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.1/EasyLanguageLearningTool-Setup-1.4.1.exe)
[![Download for Apple Silicon](https://img.shields.io/badge/macOS-Apple_Silicon_v1.4.1-000000?logo=apple&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.1/EasyLanguageLearningTool-1.4.1-Apple-Silicon.dmg)
[![Download for Intel Mac](https://img.shields.io/badge/macOS-Intel_v1.4.1-555555?logo=apple&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.1/EasyLanguageLearningTool-1.4.1-Intel.dmg)

[![Download for Android](https://img.shields.io/badge/Download_for_Android-v0.2.6-3DDC84?logo=android&logoColor=white)](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/download/v1.4.1/EasyLanguageLearningTool-Android-0.2.6.apk)

**Windows users need the `.exe`; Android users need the `.apk`; Mac users need the `.dmg` matching their processor.**
[Release notes, checksums, and build provenance](https://github.com/ReneGreblicki/Easy-Language-Learning-Tool/releases/tag/v1.4.1)

> The installer is not yet Authenticode-signed, so Windows may display an Unknown Publisher or SmartScreen warning.
> The macOS apps are ad-hoc signed but not Apple-notarized, so Gatekeeper may require **Open** from the app's context menu on first launch.

Easy Language Learning Tool is a Windows and macOS desktop application for creating
structured language-learning sentence workbooks and turning those workbooks
into one natural-sounding, resumable MP3 or desktop flashcards. Its Android
companion app synchronizes desktop-generated decks for flashcards, alternating audio,
and list study, with optional offline storage.

## What the desktop application does

- Creates structured bilingual workbooks from ranked vocabulary with configurable
  languages, CEFR levels, sentence styles, translations, and word forms.
- Generates two-sided flashcards for words, sentences, or both, using all rows or a
  selected rank range.
- Produces natural-sounding MP3 lessons with configurable voices, pacing, pauses,
  progress recovery, and safe resume after interruption.
- Stores recent workbooks and audio in History and can upload generated decks, with
  optional TTS audio, to the user's synchronized account.

## What the mobile application does

- Downloads synchronized desktop-generated decks and keeps them available offline.
- Presents each deck as flashcards, a bilingual list, or paired learning-and-translation
  audio for words, sentences, or both.
- Supports all rows or selected rows, male or female voices, playback speed and pause
  controls, session progress, and the established light and dark themes.
- Optionally downloads desktop-generated TTS audio; otherwise it uses compatible voices
  installed on the Android or iOS device.
- Removes decks only from the mobile device. The corresponding desktop files remain unchanged
  and are neither deleted nor archived.

## How to learn effectively with the app

The guidance below connects the application's features to established vocabulary-learning
research. Research findings are identified separately from practical routines suggested for
using the app; the suggested quantities and schedules are starting points, not universal
optimums.

### 1. Build a useful high-frequency foundation

Frequency matters because common words account for a large proportion of ordinary language
input. Nation's coverage analysis supports prioritising high-frequency vocabulary, while also
showing that substantially more than 1,000 word families are needed for high coverage of
unsimplified speech and writing.

Use **Sentence Creation** to begin with vocabulary relevant to everyday communication and your
goals. Treat the first 1,000 ranked words as a practical milestone, not a scientifically proven
point at which unrestricted immersion becomes optimal. Continue expanding your vocabulary
after that milestone and adjust the material to your comprehension.

### 2. Learn meanings clearly, then revisit the words in sentences

A translated example sentence by itself has not consistently outperformed a direct
word–translation pair, while repeated encounters in meaningful contexts can strengthen
different aspects of word knowledge.

Use the app in this order:

1. Open **List** mode to inspect each learning-language word directly above its translation.
2. Read the matching learning-language sentence and its translation.
3. Notice how the word changes meaning or grammatical form in the sentence.
4. Revisit the same word in new, understandable material outside the app.

One generated sentence per word is a useful starting context, not sufficient evidence of full
word knowledge.

### 3. Use flashcards for active recall

Retrieval-practice research shows that trying to recall an answer strengthens delayed
retention more effectively than repeatedly studying material without retrieval.

In **Flashcards**:

1. Read the learning-language side.
2. Pause and try to say or think of the translation before turning the card.
3. Press **Turn** only after making a genuine retrieval attempt.
4. Turn the card back and try the reverse direction when useful.
5. Use **Previous**, **Next**, and **Reshuffle** to continue through the chosen set.

Do not turn every card immediately. The effort to retrieve the answer is the important part of
the exercise.

### 4. Study manageable row ranges

Use **Selected rows** to divide a large workbook into manageable groups. A practical starting
point is 5–10 new rows per day, followed by older material, but this is an adjustable workload
rather than a research-established optimum.

Use:

- **Words** when establishing meanings.
- **Sentences** when practising comprehension in context.
- **Words and sentences** when connecting both forms.
- **All rows** for broad review after smaller ranges are becoming familiar.

Increase or reduce the range according to recall accuracy, available time, and fatigue.

### 5. Space reviews across days

A meta-analysis of second-language vocabulary experiments found a medium-to-large advantage
for spaced practice, with longer spacing generally helping delayed retention. The application
remembers the mobile study position, but it does not calculate a formal spaced-repetition
schedule automatically.

A practical starting schedule is:

- First review: later the same day or the next day.
- Second review: about 2–3 days later.
- Third review: about one week later.
- Later reviews: extend the interval when recall is successful; shorten it when recall fails.

This schedule is a usable implementation of spacing, not a uniquely proven optimal timetable.

### 6. Reinforce learning through repeated, understandable context

Repeated encounters can improve vocabulary knowledge, and reading, listening, and viewing can
all produce incidental learning. Use generated workbook sentences as an initial context, then
look for the same vocabulary in graded readers, short clips, conversations, or other material
you can mostly understand.

When encountering a studied word:

1. Try to understand it from the surrounding context.
2. Check the meaning when necessary.
3. Replay or reread the passage.
4. Return to the relevant app rows later.

Treat guesses from context as provisional until checked.

### 7. Use audio for listening and pronunciation support

On desktop, generate TTS audio or include optional TTS when uploading a deck. On Android,
choose **Listen to audio** for alternating learning-language and translation-language items, or
use the speaker button on a flashcard. Select the same male or female voice preference for both
languages when compatible voices are available.

A practical routine is:

1. Listen once without reading.
2. Predict or recall the meaning.
3. Listen again while viewing the text in **List** mode.
4. Repeat the learning-language item aloud.
5. Adjust playback speed and the pause between items until the speech remains understandable.
6. Resume from the saved position during the next mobile session.

Slower playback can help analysis, but gradually return toward a comfortable natural speed.
Voice availability depends on the voices installed on the Android device or included with
desktop-generated audio.

### 8. Combine app study with accessible immersion

Nation's Four Strands framework recommends balancing meaning-focused input,
meaning-focused output, deliberate language study, and fluency development. Ordinary
television can require several thousand word families for high lexical coverage, so difficulty
should be selected by comprehension rather than by a fixed vocabulary milestone.

Begin accessible listening and reading alongside app study. Use short clips, captions or
transcripts, graded material, and repetition. Move to harder material when you can follow the
main meaning and explain or summarise it—not merely when a counter reaches 1,000 words.

### 9. Use the language yourself

The app supports deliberate study and listening, but productive use must also be practised.
After reviewing a row range:

- Say or write a new sentence using several target words.
- Describe part of your day.
- Retell a studied sentence with one detail changed.
- Have a short conversation or write a short message.
- Revisit easy audio and speak along with it for fluency.

Producing 3–5 sentences is a manageable starting task, not an experimentally validated daily
dose.

### 10. Recommended study cycle

A balanced 20–30 minute session can be:

1. **List — 3–5 minutes:** inspect 5–10 new rows and their sentences.
2. **Flashcards — 8–10 minutes:** retrieve answers before pressing **Turn**.
3. **Listen to audio — 5–10 minutes:** alternate both languages, then repeat the
   learning-language items aloud.
4. **Active use — 3–5 minutes:** produce a few original sentences.
5. **Review:** return to older row ranges on later days using expanding intervals.

For longer sessions, increase time gradually rather than adding so many new rows that careful
retrieval and review become impossible.

### Measuring progress

Use several indicators rather than a single vocabulary count:

- Can you recall the meaning before turning a card?
- Can you understand the word in an unfamiliar sentence?
- Can you recognise it in speech without seeing the text?
- Can you produce an appropriate sentence with it?
- Can you summarise the main meaning of accessible audio or video?

Vocabulary coverage helps select material, but it is not itself a complete comprehension score.

### Research references

- Nation, I. S. P. (2006). *How large a vocabulary is needed for reading and listening?*
  Canadian Modern Language Review, 63(1), 59–82.
  [https://doi.org/10.3138/cmlr.63.1.59](https://doi.org/10.3138/cmlr.63.1.59)
- Nation, I. S. P. (2007). *The Four Strands.* Innovation in Language Learning and
  Teaching, 1(1), 2–13.
  [https://doi.org/10.2167/illt039.0](https://doi.org/10.2167/illt039.0)
- Webb, S. (2007). *Learning word pairs and glossed sentences: The effects of a single
  context on vocabulary knowledge.* Language Teaching Research, 11(1), 63–81.
  [https://doi.org/10.1177/1362168806072463](https://doi.org/10.1177/1362168806072463)
- Webb, S. (2007). *The effects of repetition on vocabulary knowledge.* Applied
  Linguistics, 28(1), 46–65.
  [https://doi.org/10.1093/applin/aml048](https://doi.org/10.1093/applin/aml048)
- Karpicke, J. D., & Roediger, H. L. III (2008). *The critical importance of retrieval
  for learning.* Science, 319(5865), 966–968.
  [https://doi.org/10.1126/science.1152408](https://doi.org/10.1126/science.1152408)
- Webb, S., & Rodgers, M. P. H. (2009). *Vocabulary demands of television programs.*
  Language Learning, 59(2), 335–366.
  [https://doi.org/10.1111/j.1467-9922.2009.00509.x](https://doi.org/10.1111/j.1467-9922.2009.00509.x)
- Feng, Y., & Webb, S. (2020). *Learning vocabulary through reading, listening, and
  viewing: Which mode of input is most effective?* Studies in Second Language
  Acquisition, 42(3), 499–523.
  [https://doi.org/10.1017/S0272263119000494](https://doi.org/10.1017/S0272263119000494)
- Kim, S. K., & Webb, S. (2022). *The effects of spaced practice on second language
  learning: A meta-analysis.* Language Learning, 72(1), 269–319.
  [https://doi.org/10.1111/lang.12479](https://doi.org/10.1111/lang.12479)

## End-user setup

1. Windows: run `EasyLanguageLearningTool-Setup-1.4.1.exe` and accept the default
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
8. For mobile study, sign in to the same account on the desktop and mobile applications,
   then upload a generated deck from the desktop. Transferring desktop TTS audio is optional.
9. On Android, download the deck from **My decks**, choose **Flashcards**, **Listen to audio**,
   or **List**, then select Words, Sentences, or both and All rows or Selected rows.
10. Choose a male or female voice where available. Audio mode also provides speed and
    inter-item pause controls and resumes from the previous saved position.

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
credentials are available. The workflow automatically switches to Developer ID signing and
notarization when the complete protected-secret set documented in
`docs/APPLE_PLATFORM_PLAN.md` is configured; otherwise it preserves the tested ad-hoc build.

## iOS signed distribution

**Status: paused for a future release.** The existing implementation and workflows are retained
so work can resume when iOS distribution is requested.

The regular iOS workflow produces tested Simulator and unsigned device bundles without exposing
signing material. Maintainers can run **iOS signed distribution** manually after configuring the
Apple Distribution certificate, App Store provisioning profile, Team ID, and optional App Store
Connect API credentials listed in `docs/APPLE_PLATFORM_PLAN.md`. It produces a signed IPA and can
optionally upload that IPA to TestFlight. Physical-iPhone acceptance remains a required human gate.

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
and mouse-wheel protections introduced in v1.3.0. The current desktop release is
**v1.4.1**, and the current Android companion is **v0.2.6**. iOS distribution is paused
for a future release. The latest
workflow is: generate a deck on desktop, sign in and upload it, then sign in to the same
account on mobile and download it for offline Flashcards,
Listen to audio, or List study. Desktop TTS transfer is optional, and removing a deck
from mobile never deletes or archives the desktop file.

## Project documentation

- `resources/USER_MANUAL.md` is the offline guide shown by the Information tab.
- `docs/SPEC_TRACEABILITY.md` maps every approved requirement to code and tests.
- `docs/RELEASE_READINESS.md` defines automated and external release gates.
- `docs/ANDROID_PROJECT_PLAN.md` documents mobile synchronization and study workflows.
- `docs/ANDROID_DEVICE_VERIFICATION.md` provides the real-device acceptance checklist.
- `docs/APPLE_PLATFORM_PLAN.md` covers the iOS companion and macOS packaging workflow.
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

# 5. Desktop cloud synchronization

## 5.1 Account setup

Open **Sync**, enter the same email address and password used by the mobile app,
and select **Sign in**. **Keep me signed in** stores only the renewable session in
Windows Credential Manager or macOS Keychain; the password is never stored.

Create an account in the mobile app or desktop Sync panel if you do not already have one. Email
confirmation may be required before the first sign-in.

The confirmation link should reopen the mobile app. If it opens a broken `localhost`
page, the project administrator must add
`com.renegreblicki.easylanguageflashcards://login-callback/**` under Supabase
**Authentication → URL Configuration → Redirect URLs**.

## 5.2 Upload a deck

1. Load the workbook in **Flashcards**.
2. Open **Sync** and sign in.
3. Optionally enable **Include available desktop TTS audio**. It is off by default and
   uploads only clips already generated for this workbook.
4. Select **Upload current deck**.
5. Sign in to the mobile app with the same account and refresh **My decks**.
6. Open the deck once to keep its text on the device. Audio is cached only when explicitly
   selected in the activity settings.

Deck and card identifiers remain stable when the same workbook is uploaded again.
Interrupted uploads remain in a durable queue; use **Retry pending uploads** after
the connection returns. Uploading never relocates, edits, archives, or deletes the
desktop workbook.

---

# 6. Android and iOS study companions

The mobile companion provides flashcards, audio playback, and a list view. It does not
generate workbooks; content comes from the Windows or macOS desktop application.

## 6.1 Sign in, choose an activity, and optionally download audio

Sign in with the same account as desktop and open a deck. Choose **Flashcards**, **Listen to
audio**, or **View list**, then choose Words, Sentences, or both and all rows or a selected
rank range. Desktop TTS audio is transferred only when enabled during desktop upload and is
downloaded to the device only when **Download desktop TTS audio** is selected. If a transferred
clip is unavailable or cannot be opened, the mobile app uses an installed voice for the learner
language instead, so audio playback does not depend on desktop audio being uploaded. Flashcard
and audio settings let the user select a female or male phone voice. The same selection is
applied to both the learning and translation languages. Transferred clips are retained only
as an offline fallback if the requested phone voice cannot be used.

## 6.2 Flashcards, audio, and list

Flashcards remain two-sided with Previous, Turn, Next, Reshuffle, and a large sound button
at 75% card height without a visible guide line. Audio playback includes every selected word
or sentence and its translation, uses the selected phone voice for both languages, and
resumes the saved track for the same deck, mode, and range. The app matches the closest
installed regional voice when the exact learner-language locale is unavailable. List view
places each foreign value directly above its translation, uses distinct established palette
colours, and shows its draggable scrollbar only while the list is moving.

Audio mode alternates each learning-language item with its translation: learning word,
translated word, learning sentence, translated sentence. A horizontal speed adjustment sits
under Previous, Play/Stop, and Next, with only **−2×** to the left and **2×** to the right.
The centre is normal speed but is intentionally unlabelled. Each item is followed by a
0.5-second break by default. Use the timer button to the right of the speed control to select
a break from 0 to 2 seconds.

Use the brightness icon in **My decks** or the study screen to switch between the
desktop application's light and dark palettes. The Android launcher uses the same
application icon as the Windows and macOS versions. The iOS adaptation uses the same workflow,
layout, palette, account, synchronized data, and two-language voice preference.

## 6.3 Phone-only removal

Choose **Remove download** to erase only that mobile installation's cached deck
and audio. The synchronized cloud deck, the desktop database, and every desktop
workbook remain unchanged—not deleted and not archived. The deck can be downloaded
again later.

**Delete everywhere** soft-deletes only the synchronized cloud copy and removes the
device download. The original desktop workbook and desktop files remain unchanged.
The cloud copy has a 30-day recovery period before permanent removal.

To recover it, select the **Cloud Trash** icon in **My decks**, find the deck, and
select **Restore**. Restoration recreates the cloud-library entry; download it again
on any device that needs an offline copy.

---

# 7. Offline and internet requirements

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
| Sign in or synchronize a deck | Yes |
| Download a mobile deck and audio | Yes |
| Study an already downloaded mobile deck | No |

Cloud generation sends the necessary prompt content to the selected AI provider. Edge TTS sends the text required for speech synthesis to Microsoft’s service.

---

# 8. Common problems

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

## A desktop deck does not appear on mobile

- Confirm both apps use the same account.
- In desktop **Sync**, select **Retry pending uploads**.
- Refresh **My decks** on the mobile app while online.
- If the saved desktop session expired, sign in again and retry.

## The mobile app cannot reach the sign-in server

On Android, use v0.2.2 or newer. Versions 0.2.0 and 0.2.1 were release builds with a missing
main-manifest internet permission; older debug versions were not affected. On iOS, use the
current preview generated by the iOS workflow.

- Confirm that normal websites open on the phone.
- Temporarily disable VPN, Private DNS, firewall, or ad-blocking applications.
- Switch between Wi-Fi and mobile data, then try again.
- If the message persists on both networks, check the Supabase project status.

Technical authentication, network, synchronization, storage, and audio failures are converted
into descriptive user-facing messages without exposing raw server URLs or exception details.
