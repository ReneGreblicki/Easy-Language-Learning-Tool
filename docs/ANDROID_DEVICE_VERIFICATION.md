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

## 2. Persistent offline deck

1. Download and open the deck.
2. Close the app completely.
3. Enable airplane mode.
4. Reopen the app and deck.
5. Open the activity chooser and test Flashcards, Listen to audio, and View list.
6. In every activity, test Words, Sentences, and Words and sentences.
7. Test all rows and a selected inclusive row range.
8. Confirm list order and foreign/translation colours.
9. Pause audio, leave, reopen the same selection, and confirm it resumes at that track.
10. Confirm audio is not downloaded unless the optional box is enabled.
11. Flip cards by tapping and by pressing **Turn**; test Previous, Next, and Reshuffle.
12. Confirm the sound button works, leaves loading state, and has no visible guide line.
13. Switch between the light and dark desktop-matched themes.

Pass: the deck remains in the library, each card has only Front and Back, every selected
field is readable, controls behave like desktop, and cached audio replays offline.

## 3. Phone-only removal safety

1. Record the desktop workbook path and checksum.
2. On Android, choose **Remove download** and confirm.
3. Refresh the Android library and inspect the desktop History and Flashcards tabs.

Pass: only the phone's cached deck/audio disappears. The cloud library entry, desktop
database, workbook path, workbook checksum, and desktop History entry are unchanged.

## 4. Cloud soft deletion and restore

1. Download the deck again.
2. Choose **Delete everywhere** and confirm.
3. Verify it leaves **My decks** and appears in **Cloud Trash**.
4. Verify the desktop workbook and History entry remain unchanged.
5. Select **Restore** in Cloud Trash and refresh My decks.

Pass: the cloud entry is hidden and restored as expected, the phone cache is removed, and
no desktop file is moved, archived, edited, or deleted.

## 5. Result record

| Field | Result |
|---|---|
| Phone model | |
| Android version | |
| Commit SHA | |
| APK SHA-256 | |
| Account/upload | Pass / Fail |
| Offline deck/audio | Pass / Fail |
| Study modes/range/navigation/theme | Pass / Fail |
| Phone-only removal | Pass / Fail |
| Trash/restore | Pass / Fail |
| Notes | |

Do not promote the Android artifact to a signed production release until every row passes.
