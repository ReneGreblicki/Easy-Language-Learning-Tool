import 'package:easy_language_flashcards/audio/android_speech_engine.dart';
import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('Android card speech uses the public-API bridge and returns on start', () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      calls.add(call);
      if (call.method == 'getLanguages') return ['de-DE'];
      if (call.method == 'getVoices') return [];
      return 1;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
    await DeviceSpeech(engine: AndroidSpeechEngine()).speak('lernen. Ich lerne jeden Tag.', 'German');
    expect(calls.singleWhere((c) => c.method == 'awaitSpeakCompletion').arguments, false);
    expect(calls.singleWhere((c) => c.method == 'speak').arguments,
      {'text': 'lernen. Ich lerne jeden Tag.', 'focus': true});
  });

  test('native rejection reaches the caller with a useful device error', () async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      if (call.method == 'getLanguages') return ['de-DE'];
      if (call.method == 'getVoices') return [];
      if (call.method == 'speak') {
        throw PlatformException(code: 'TTS_SPEAK_REJECTED', message: 'The engine rejected speech.');
      }
      return 1;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
    await expectLater(DeviceSpeech(engine: AndroidSpeechEngine()).speak('lernen', 'German'),
      throwsA(isA<PlatformException>().having((error) => speechErrorText(error),
        'error text', contains('TTS_SPEAK_REJECTED'))));
  });
}
