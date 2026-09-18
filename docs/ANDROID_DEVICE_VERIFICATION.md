# Android Physical-Device Verification

Use this checklist after the automated Android workflow succeeds. Record the phone model,
Android version, APK commit, tester, and UTC date.

## Prerequisites

- Apply every SQL file in `supabase/migrations` in numeric order.
- Create or confirm one Supabase email/password account.
- Install the APK artifact built from the current pull-request commit.
- Install the matching desktop pull-request build on Windows or macOS.

## 1. Account and desktop upload

1. Sign in to Android and desktop with the same account.
2. Generate or load a small workbook on desktop.
3. Generate TTS for the same workbook, enable **Include available desktop TTS audio**, then
   select **Upload current deck**.
4. Refresh **My decks** on Android.

Pass: the deck title, language pair, order, and all four text fields match the workbook.

Regression note: Android v0.2.0 and v0.2.1 release APKs omitted the main-manifest internet
permission and therefore could not contact Supabase. Verification must use v0.2.2 or newer.

## 2. Error messages

1. Disable Wi-Fi and mobile data, then attempt to sign in.
2. Confirm the app explains that the server cannot be reached and suggests connection checks.
3. Confirm no exception name, API URL, hostname, database code, or stack detail is displayed.
4. Restore connectivity and enter an incorrect password; confirm the app identifies incorrect
   email/password without exposing the server response.

Pass: every failure is descriptive and actionable, with no raw technical details.

## 3. Persistent offline deck

1. Download and open the deck.
2. Close the app completely.
3. Enable airplane mode.
4. Reopen the app and deck.
5. Use each landing-page practice action and test Flashcards, Audio, and List.
6. In every activity, test Words, Sentences, and Words and sentences.
7. Test all rows and a selected inclusive row range.
8. Confirm list order and foreign/translation colours.
9. Stop audio, leave, reopen the same selection, and confirm it resumes at that track.
10. Confirm audio is not downloaded unless the optional box is enabled.
11. Flip cards by tapping and by pressing **Turn**; test Previous, Next, and Reshuffle.
12. Test learning- and translation-language playback. Confirm the closest installed regional
    voice is used when the exact locale is unavailable.
13. Select female and male phone voices. For each selection, confirm both learning and
    translation playback use that gender when suitable voices are installed.
14. In Audio, confirm the order is learning word, translated word, learning sentence,
    translated sentence for each row.
15. Confirm the speed control shows only −2× left of the bar and 2× right of the bar, with no
    text, number, popup label, or normal-speed marker above it.
16. Confirm the default break is 0.5 seconds, then test shorter and longer break selections.
17. Confirm the sound button works on both card sides, leaves loading state, and has no
    visible guide line.
18. Scroll the list, drag the scrollbar thumb to fast-scroll, and confirm it fades afterward.
19. Switch between the light and dark desktop-matched themes.

Pass: the deck remains in the library, each card has only Front and Back, every selected
field is readable, controls behave like desktop, and cached audio replays offline.

## 4. Phone-local removal and delayed cloud cleanup

1. Record the desktop workbook path and checksum.
2. In Android folder management, choose **Remove download** and confirm.
3. Refresh the Android library and inspect desktop History and Flashcards.

Pass: the phone's cached deck/audio disappears immediately. The cloud deck is marked
for cleanup after 14 days and hidden from the active mobile library. Desktop files,
their checksums, and desktop History remain unchanged.

## 5. Cleanup cancellation and desktop isolation

1. Download or use the removed deck again within 14 days through the available
   recovery/download flow. Record a failure if that flow is not reachable.
2. Verify pending cleanup markers are cleared and the deck is available offline.
3. Using a disposable test deck and a test backend, verify due cleanup removes its
   cloud cards, progress, audio metadata, stored audio, and deck record.
4. Verify the original desktop workbook checksum and History entry remain unchanged.
5. Verify no 90-day inactivity purge runs and no **Delete everywhere** or **Cloud
   Trash** control is exposed in the mobile landing header or deck manager.

Pass: use/download cancels pending removal; due cleanup respects the 14-day policy;
no desktop file is moved, archived, edited, or deleted.

## 6. Multilingual background generation

1. Install Android 0.5.0 from the verified PR artifact. Confirm the deployed generation
   backend supports the new language codes before testing new-language requests.
2. Confirm all 24 language/script options appear in learning and translation controls.
3. Generate a small deck in an added Latin-script language and another in Chinese,
   Japanese, Korean, Malayalam, or Russian. Check readable text and translations.
4. Start at rank 4,901 and verify the maximum is 100 base words before extra-form limits.
5. While generating, study an existing deck, then close the app. Reopen it and verify
   job progress or the completed deck is restored without duplicate cards.
6. Download the new deck, enable airplane mode, and verify Flashcards, Audio, and List.
7. Check installed TTS voice availability for the chosen languages and replay both sides.
8. Verify the selected language restores its own selected deck after switching languages.

Pass: complete decks use the requested ranked range and language pair, background
jobs survive app closure, and downloaded text remains usable offline. Record voice
availability separately from corpus and generation results.

## 7. Result record

| Field | Result |
|---|---|
| Phone model | |
| Android version | |
| Commit SHA | |
| APK SHA-256 | |
| Account/upload | Pass / Fail |
| Offline deck/audio | Pass / Fail |
| Study modes/range/navigation/theme | Pass / Fail |
| Phone-local removal | Pass / Fail |
| 14-day cleanup/cancellation | Pass / Fail |
| Desktop file preservation | Pass / Fail |
| Multilingual generation | Pass / Fail |
| Background generation/reopening | Pass / Fail |
| New-language TTS availability | Available / Unavailable; locale/engine |
| Notes | |

Do not promote the Android artifact to a signed production release until every row passes.
