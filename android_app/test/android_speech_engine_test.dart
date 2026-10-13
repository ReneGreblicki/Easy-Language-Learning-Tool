import 'dart:async';
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

  testWidgets('slow native start remains eligible within the bridge deadline', (tester) async {
    final started = Completer<int>();
    var requested = false;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      if (call.method == 'getLanguages') return ['de-DE'];
      if (call.method == 'getVoices') return [];
      if (call.method == 'speak') { requested = true; return started.future; }
      return 1;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
    final outcome = DeviceSpeech(engine: AndroidSpeechEngine()).speak('lernen', 'German')
        .then<Object?>((_) => 'started', onError: (Object error) => error);
    await tester.pump();
    expect(requested, true);
    await tester.pump(const Duration(seconds: 5));
    started.complete(1);
    await tester.pump();
    expect(await outcome, 'started');
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
