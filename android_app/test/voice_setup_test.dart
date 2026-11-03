import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:easy_language_flashcards/audio/voice_setup.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('deck open offers missing voices, then rechecks installation on return', (tester) async {
    final speech = SetupSpeech();
    await tester.pumpWidget(MaterialApp(home: DeckVoiceSetup(
      speech: speech, languages: const ['European Spanish', 'US English'],
      builder: (_) => const Scaffold(body: Text('Deck content')))));
    await tester.pumpAndSettle();
    expect(find.text('Offline voices'), findsOneWidget);
    expect(find.textContaining('Download needed: Spanish'), findsOneWidget);
    expect(speech.checked, ['European Spanish', 'US English']);
    await tester.tap(find.text('Download voices'));
    await tester.pumpAndSettle();
    expect(speech.downloads, 1);
    // Returning without finishing a download must not claim readiness.
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();
    expect(speech.refreshes, 1);
    expect(find.textContaining('Download needed: Spanish'), findsOneWidget);
    expect(find.textContaining('ready for offline use'), findsNothing);
    speech.missing = [];
    await tester.tap(find.text('Check again'));
    await tester.pumpAndSettle();
    expect(find.textContaining('ready for offline use'), findsOneWidget);
    await tester.tap(find.text('Continue to deck'));
    await tester.pumpAndSettle();
    expect(find.text('Deck content'), findsOneWidget);
  });

  testWidgets('installed voices are reused without prompting on another deck', (tester) async {
    final speech = SetupSpeech()..missing = [];
    await tester.pumpWidget(MaterialApp(home: DeckVoiceSetup(
      speech: speech, languages: const ['Spanish', 'US English'],
      builder: (_) => const Scaffold(body: Text('Another deck')))));
    await tester.pumpAndSettle();
    expect(find.text('Offline voices'), findsNothing);
    expect(find.text('Another deck'), findsOneWidget);
    expect(speech.downloads, 0);
  });

  testWidgets('voice check failure permits reading and reports the failure', (tester) async {
    final speech = SetupSpeech()..failCheck = true;
    await tester.pumpWidget(MaterialApp(home: DeckVoiceSetup(
      speech: speech, languages: const ['Spanish', 'US English'],
      builder: (_) => const Scaffold(body: Text('Deck content')))));
    await tester.pumpAndSettle();
    expect(find.text('Deck content'), findsOneWidget);
    expect(find.textContaining('voice list unavailable'), findsOneWidget);
    expect(speech.downloads, 0);
  });
}

class SetupSpeech extends DeviceSpeech {
  List<String> missing = ['European Spanish'];
  List<String>? checked;
  bool failCheck = false;
  int downloads = 0;
  int refreshes = 0;
  @override
  bool get supportsVoiceInstallation => true;
  @override
  Future<List<String>> missingOfflineLanguages(Iterable<String> languages) async {
    checked = languages.toList();
    if (failCheck) throw StateError('voice list unavailable');
    return missing;
  }
  @override
  Future<void> installVoiceData() async { downloads++; }
  @override
  Future<void> refreshVoiceData() async { refreshes++; }
  @override
  Future<void> stop() async {}
}
