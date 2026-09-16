# Mobile Landing Page Build Plan

## Product outcome

Replace the deck-list-first Android home screen with a task-oriented landing page while keeping
authentication, synchronization, offline storage, deletion rules, themes, generation, and every
existing study control unchanged.

## Landing-page actions

1. **Select a language** filters decks by learning/source language.
2. **Select a deck** selects one matching deck for every practice activity.
3. **Generate a new deck** opens the existing protected generation workflow.
4. **Practice flashcards** opens the existing Flashcard setup for the active deck.
5. **Practice audio** opens the existing Audio setup for the active deck.
6. **Practice list** opens the existing List setup for the active deck.
7. **Further learning** collects media, genre, CEFR level, and duration preferences.
8. **Learning instructions** presents the complete app and general-learning roadmap.

## Selection state

- Persist the active learning language locally.
- Persist one last-selected deck ID per learning language.
- Filter using `Deck.sourceLanguage`; never use `translationLanguage`.
- Clear an invalid selection after deletion, synchronization changes, or language mismatch.
- If a practice action has no deck, open the filtered picker and continue to that activity.
- After successful phone generation, select the new deck and its language automatically.
- Device-local selection state must not be synchronized as deck data.

## Further Learning contract

Inputs:

- media: YouTube video, podcast, series, movie, or song;
- genre: a media-specific choice;
- level: A1–C2;
- duration: under 5, 5–15, 15–30, 30–60, or 60+ minutes;
- language: inherited from the landing page.

Duration is hidden and omitted for songs. The first implementation records and validates the
request and presents a tailored search summary. Provider-backed recommendations are a separate
backend increment. Provider keys must remain in a protected server function and never enter the
APK, logs, or local selection storage.

## Learning Instructions content

1. Choose one language and a practical goal.
2. Generate a manageable high-frequency foundation.
3. Understand rows in List.
4. Retrieve answers in Flashcards before turning the card.
5. Listen, recall, and repeat with Audio.
6. Review across expanding intervals.
7. use understandable external media near the current level.
8. Produce original speech and writing.
9. Assess recall, listening, contextual understanding, production, and summarization.

Suggested quantities and intervals are labelled as adjustable routines rather than scientifically
fixed optima. The app does not claim automatic spaced repetition.

## Implementation workflow

### Phase A — Local contracts and documentation

- Record locked behavior and acceptance criteria.
- Add a local landing-selection persistence contract.
- Preserve repository test doubles.

### Phase B — Landing page and selection

- Add the landing menu.
- Add language and filtered deck pickers.
- Preserve download, phone-only removal, cloud soft deletion, restoration, sign-out, and themes.

### Phase C — Activity routing and generation

- Reuse existing setup dialogs and study screens.
- Route each practice action through the active deck.
- Continue through deck selection when needed.
- Activate a newly generated deck automatically.

### Phase D — Guidance features

- Add the Further Learning form and conditional fields.
- Add the Learning Instructions roadmap.
- Keep provider-backed media discovery behind a future authenticated service adapter.

### Phase E — Verification and release

- Run Flutter analysis and unit/widget tests.
- Run desktop quality and regression checks.
- Build an installable release APK.
- Verify on a physical Android device.
- Update README, manual, release notes, and Android version only after approval.

## Acceptance criteria

- Every requested landing action is visible and keyboard/screen-reader labelled.
- Language filtering returns only matching source-language decks.
- A separate active deck is remembered for each language.
- All three practice activities use the same active deck and existing settings.
- Missing selection produces a picker, not an error or empty study screen.
- Songs never show or submit duration.
- Learning Instructions contains the complete roadmap.
- Existing audio, list, flashcard, synchronization, removal, Trash, and generation tests remain
  green.
- No release is published until the redesigned navigation is reviewed.

## Background generation and retention extension

### Generation jobs

- Deck generation is a persistent Supabase job, not a screen-bound mobile request.
- Submitting a valid request immediately returns the user to the landing page.
- The server processes multiple generation batches concurrently and continues after the app is
  backgrounded or closed.
- The landing page displays queued, running, completed, and failed jobs while the app is open.
- Reopening the app restores job progress and refreshes completed decks.
- The configured model remains `gpt-5-mini` until a model change is explicitly approved.

### Further Learning results

- Further Learning calls an authenticated server function backed by the configured GPT model and
  web search.
- Each request returns exactly three current options with a title, concise description, direct
  link, and optional image URL.
- Songs and movies have no duration field. Series use an **Episode duration** field. YouTube and
  podcasts use **Media duration**.

### Deck lifecycle

- A user may have at most 10 active decks for one learning language.
- A locally removed deck is marked for cloud cleanup after 14 days. Redownloading or using it
  before the deadline cancels pending cleanup.
- App startup and a periodic in-app timer invoke authenticated maintenance. Purging removes the
  Supabase deck, cards, progress, metadata, and stored audio belonging to that deck.
- `last_used_at` is updated whenever a deck is opened. A future 90-day inactivity policy may use
  it, but no inactivity-based deletion is enabled in this increment.
- Desktop source files remain outside this lifecycle and are never deleted by mobile cleanup.

### Ranked-word range

- Generation accepts a one-based starting frequency rank.
- The selected base words begin at that rank; for example, 300 rows starting at rank 500 use
  ranks 500–799.
- The maximum base-word count is the smaller of the 5,000-row output limit and the remaining
  approved frequency range. The form shows a red limit message and clamps invalid values.

### Navigation and header

- Flashcards, Audio, and List always open a full intermediate settings page before study.
- The landing header has no text title and no Cloud Trash action.
- A line-only open-book/globe mark appears at the left. Theme, folder management, and sign-out
  remain available.
