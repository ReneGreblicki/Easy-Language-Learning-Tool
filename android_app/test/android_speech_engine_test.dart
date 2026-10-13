import 'dart:async';
import 'package:easy_language_flashcards/audio/android_speech_engine.dart';
import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:flutter/services.dart';
import 'package:easy_language_flashcards/generation/generation_settings.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('Android card speech uses the public-API bridge and returns on start', () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      calls.add(call);
      if (call.method == 'getLanguages') return ['de-DE'];
      if (call.method == 'getVoices') return [{'name': 'de-de-x-local', 'locale': 'de-DE', 'network_required': false}];
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
      if (call.method == 'getVoices') return [{'name': 'de-de-x-local', 'locale': 'de-DE', 'network_required': false}];
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
      if (call.method == 'getVoices') return [{'name': 'de-de-x-local', 'locale': 'de-DE', 'network_required': false}];
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

  for (final language in GenerationLanguage.values) {
    test('selects an explicit offline voice for ${language.label}', () async {
      final locale = preferredSpeechLocale(language.label);
      final voices = [
        {'name': '$locale-network-female', 'locale': locale, 'network_required': true},
        {'name': '$locale-missing', 'locale': locale, 'network_required': false,
          'features': ['notInstalled']},
        {'name': '$locale-local', 'locale': locale, 'network_required': false},
        {'name': 'unrelated', 'locale': 'xx-XX', 'network_required': false},
      ];
      final calls = <MethodCall>[];
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
        calls.add(call);
        if (call.method == 'getVoices') return voices;
        return 1;
      });
      addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
      await DeviceSpeech(engine: AndroidSpeechEngine()).speak('sample', language.label);
      expect(calls.singleWhere((c) => c.method == 'setVoice').arguments,
          {'name': '$locale-local', 'locale': locale});
      expect(calls.where((c) => c.method == 'setLanguage'), isEmpty);
      expect(calls.where((c) => c.method == 'speak').length, 1);
    });
  }

  for (final pair in {'Norwegian': 'no-NO', 'Chinese (Simplified)': 'cmn-CN',
      'Indonesian': 'in-ID', 'Spanish': 'es-MX', 'Portuguese': 'pt-BR'}.entries) {
    test('supports installed language alias or regional fallback ${pair.value}', () async {
      Map<Object?, Object?>? selected;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
        if (call.method == 'getVoices') {
          return [{'name': 'opaque-local', 'locale': pair.value, 'network_required': false}];
        }
        if (call.method == 'setVoice') selected = call.arguments as Map;
        return 1;
      });
      addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
      await DeviceSpeech(engine: AndroidSpeechEngine()).speak('sample', pair.key);
      expect(selected?['locale'], pair.value);
    });
  }

  for (final failure in ['selection', 'synthesis']) {
    test('retries another offline voice after $failure failure', () async {
      final selected = <String>[];
      var spoken = 0;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
        if (call.method == 'getVoices') {
          return [
            {'name': 'A-local', 'locale': 'es-ES', 'network_required': false},
            {'name': 'B-local', 'locale': 'es-ES', 'network_required': false},
          ];
        }
        if (call.method == 'setVoice') {
          selected.add((call.arguments as Map)['name'] as String);
          if (failure == 'selection' && selected.length == 1) return 0;
        }
        if (call.method == 'speak') {
          spoken++;
          if (failure == 'synthesis' && spoken == 1) {
            throw PlatformException(code: 'TTS_SYNTHESIS_FAILED', message: 'error -4');
          }
        }
        return 1;
      });
      addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
      await DeviceSpeech(engine: AndroidSpeechEngine()).speak('hola', 'Spanish');
      expect(selected, ['A-local', 'B-local']);
      expect(spoken, failure == 'selection' ? 1 : 2);
    });
  }

  test('missing offline data never uses a network or wrong-language voice', () async {
    var spoken = false;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      if (call.method == 'getVoices') {
        return [
          {'name': 'network', 'locale': 'es-ES', 'network_required': true},
          {'name': 'missing', 'locale': 'es-ES', 'network_required': false,
            'features': ['notInstalled']},
          {'name': 'english', 'locale': 'en-US', 'network_required': false},
        ];
      }
      if (call.method == 'speak') spoken = true;
      return 1;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
    await expectLater(DeviceSpeech(engine: AndroidSpeechEngine()).speak('hola', 'Spanish'),
        throwsA(isA<PlatformException>().having((e) => e.code, 'code', 'TTS_OFFLINE_VOICE_UNAVAILABLE')));
    expect(spoken, false);
  });

  test('stop prevents a late failed request from restarting speech', () async {
    final started = Completer<int>();
    final speaking = Completer<void>();
    var attempts = 0;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, (call) async {
      if (call.method == 'getVoices') {
        return [
          {'name': 'A-local', 'locale': 'es-ES', 'network_required': false},
          {'name': 'B-local', 'locale': 'es-ES', 'network_required': false},
        ];
      }
      if (call.method == 'speak') {
        attempts++;
        speaking.complete();
        return started.future;
      }
      return 1;
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(AndroidSpeechEngine.channel, null));
    final speech = DeviceSpeech(engine: AndroidSpeechEngine());
    final outcome = speech.speak('hola', 'Spanish').then<Object?>((_) => null,
        onError: (Object error) => error);
    await speaking.future;
    await speech.stop();
    started.complete(0);
    expect(await outcome, isA<PlatformException>().having((e) => e.code, 'code', 'TTS_CANCELLED'));
    expect(attempts, 1);
  });

}
