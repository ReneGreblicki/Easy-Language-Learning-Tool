# Apple platform adaptation plan and workflow

## 1. Scope

- Native macOS desktop packages for Apple Silicon and Intel Macs.
- Native iOS companion with the same synchronized flashcards, paired list, audio player,
  offline deck storage, deletion rules, themes, and icon as Android.
- The desktop application remains the workbook and desktop-TTS generator of record.
- iOS and Android remain study companions and do not generate workbooks.

## 2. macOS desktop workflow

1. Run the complete Python quality and test suite on each macOS architecture.
2. Build a native PySide6 application bundle with Nuitka.
3. Include resources, examples, the manual, FFmpeg, and FFprobe.
4. Use macOS Keychain for remembered API and synchronization sessions.
5. Use `afplay` for repeatable flashcard playback and Trash terminology for safe deletion.
6. Ad-hoc sign the application when Developer ID secrets are unavailable.
7. Validate the bundle, architecture, metadata, bundled tools, and offscreen launch.
8. Create separate Apple Silicon and Intel DMGs with checksums and provenance.
9. Developer ID sign and notarize before unrestricted public distribution.

## 3. iOS companion workflow

1. Generate the current Flutter iOS platform shell on a macOS runner.
2. Apply the stable bundle identifier, app name, iOS 13 deployment target, callback URL scheme,
   encryption declaration, and desktop-matched icon.
3. Resolve Flutter/CocoaPods dependencies.
4. Run mobile configuration tests, Dart analysis, and all unit/widget tests.
5. Build and validate a release-mode iOS Simulator application.
6. Publish the simulator ZIP, checksum, and provenance as a CI artifact.
7. After Apple credentials are supplied, import the distribution certificate and provisioning
   profile, build a signed IPA, upload it to TestFlight, and complete physical-device checks.

## 4. Shared mobile behavior

- Same email/password account and Supabase data as Android and desktop.
- Same home library, activity chooser, content mode, and inclusive row selection.
- Same two-sided flashcards with Previous, Turn, Next, Reshuffle, and sound.
- Same paired list with auto-hiding draggable scrollbar.
- Same resumable alternating learning/translation audio, speed, pause, and voice-gender controls.
- Apple voice selection uses iOS voice gender and identifier metadata when available.
- Downloaded decks remain offline on the device.
- Remove download affects only that mobile installation. Desktop and cloud copies remain
  unchanged.
- Delete everywhere soft-deletes the synchronized cloud copy with the existing recovery period
  but never modifies desktop files.

## 5. Human-gated release inputs

The code, simulator build, and unsigned Mac DMGs can be completed without user input. Physical
iPhone distribution requires:

- Apple Developer team ID.
- Apple Distribution certificate exported as a password-protected P12.
- Certificate password.
- App Store provisioning profile for `com.renegreblicki.easylanguagelearningtool`.
- App Store Connect application record and API credentials for TestFlight upload.
- Tests on at least one supported iPhone.

macOS Gatekeeper-free distribution additionally requires a Developer ID Application certificate
and Apple notarization credentials.

## 6. Definition of done

- Both macOS architectures build, launch, and package successfully.
- The iOS Simulator build passes analysis, tests, and metadata validation.
- Authentication confirmation and password reset return to the iOS app.
- Both language sides play with the selected voice gender where compatible system voices exist.
- Offline deck, list, flashcard, audio-resume, theme, and local-removal tests pass.
- Signed physical-device and TestFlight delivery remain explicitly blocked until Apple
  credentials are available.
