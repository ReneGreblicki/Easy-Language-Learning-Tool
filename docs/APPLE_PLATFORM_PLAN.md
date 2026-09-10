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
9. When the signing secrets are configured, import the Developer ID certificate, enable the
   hardened runtime, sign the app and DMG, submit the DMG to Apple, staple the notarization
   ticket, validate it, and record the result in build provenance.

## 3. iOS companion workflow

1. Generate the current Flutter iOS platform shell on a macOS runner.
2. Apply the stable bundle identifier, app name, iOS 13 deployment target, callback URL scheme,
   encryption declaration, and desktop-matched icon.
3. Resolve Flutter/CocoaPods dependencies.
4. Run mobile configuration tests, Dart analysis, and all unit/widget tests.
5. Build and validate a debug iOS Simulator application plus an unsigned release-mode iPhone
   application.
6. Publish both ZIPs, their checksums, and provenance as CI artifacts. The unsigned iPhone
   bundle is a signing input and cannot be installed on a physical device as distributed.
7. The manual `iOS signed distribution` workflow validates the Apple secrets, imports the
   distribution certificate and provisioning profile into an ephemeral keychain, configures
   manual Xcode signing, builds a signed IPA, and optionally uploads it to TestFlight.
8. Signing material is removed from the runner after every workflow outcome.
9. Complete authentication, audio, offline-storage, and deletion checks on a physical iPhone.

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

Repository secret names:

- iOS: `APPLE_DISTRIBUTION_CERTIFICATE_BASE64`,
  `APPLE_DISTRIBUTION_CERTIFICATE_PASSWORD`, `APPLE_KEYCHAIN_PASSWORD`,
  `APPLE_PROVISIONING_PROFILE_BASE64`, and `APPLE_TEAM_ID`.
- macOS: `MACOS_DEVELOPER_ID_CERTIFICATE_BASE64`,
  `MACOS_DEVELOPER_ID_CERTIFICATE_PASSWORD`, `MACOS_KEYCHAIN_PASSWORD`, and
  `MACOS_SIGNING_IDENTITY`.
- TestFlight and notarization: `APP_STORE_CONNECT_KEY_ID`,
  `APP_STORE_CONNECT_ISSUER_ID`, and `APP_STORE_CONNECT_API_KEY_BASE64`.

The Base64 values must contain only the encoded P12, provisioning profile, or App Store Connect
private-key bytes. The workflows decode them only on an ephemeral GitHub-hosted runner.

## 6. Definition of done

- Both macOS architectures build, launch, and package successfully.
- The iOS Simulator build passes analysis, tests, and metadata validation.
- Authentication confirmation and password reset return to the iOS app.
- Both language sides play with the selected voice gender where compatible system voices exist.
- Offline deck, list, flashcard, audio-resume, theme, and local-removal tests pass.
- Signed physical-device, TestFlight, Developer ID, and notarized delivery workflows are ready;
  execution remains blocked until Apple credentials are configured.
