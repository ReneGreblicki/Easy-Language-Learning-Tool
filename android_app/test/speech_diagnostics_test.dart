import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:easy_language_flashcards/audio/speech_diagnostics_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('voice test presents device errors and lets the user switch engine', (tester) async {
    final speech = DiagnosticSpeech();
    await tester.pumpWidget(MaterialApp(home: SpeechDiagnosticsScreen(
      speech: speech, language: 'German', sampleText: 'lernen')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Test English'));
    await tester.pumpAndSettle();
    expect(find.textContaining('TTS_SYNTHESIS_FAILED'), findsOneWidget);
    expect(speech.testedLanguage, 'US English');
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Google speech services').last);
    await tester.pumpAndSettle();
    expect(speech.selected, 'com.google.android.tts');
  });
}

class DiagnosticSpeech extends DeviceSpeech {
  String? selected;
  String? testedLanguage;
  @override
  Future<Map<String, Object?>> diagnostics() async => {
    'engine': selected ?? 'com.samsung.SMT',
    'engines': ['com.samsung.SMT', 'com.google.android.tts'],
  };
  @override
  Future<void> selectEngine(String engine) async { selected = engine; }
  @override
  Future<void> speak(String text, String language, {bool awaitCompletion = false,
    SpeechVoiceGender gender = SpeechVoiceGender.female, double speedFactor = 1}) async {
    testedLanguage = language;
    throw PlatformException(code: 'TTS_SYNTHESIS_FAILED', message: 'Voice data is missing.');
  }
  @override
  Future<void> stop() async {}
}
