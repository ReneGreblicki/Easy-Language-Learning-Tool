import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('prefers downloaded offline voices over network and missing voices', () {
    expect(
      chooseBestSpeechVoice('Spanish', SpeechVoiceGender.female, [
        {
          'name': 'female network',
          'locale': 'es-ES',
          'network_required': 'true',
        },
        {
          'name': 'female missing',
          'locale': 'es-ES',
          'features': '[notInstalled]',
        },
        {'name': 'local', 'locale': 'es-MX', 'network_required': 'false'},
      ])?['name'],
      'local',
    );
  });

  test('female metadata does not also count as male', () {
    expect(
      chooseBestSpeechVoice('Spanish', SpeechVoiceGender.female, [
        {'name': 'A neutral', 'locale': 'es-ES'},
        {'name': 'Z woman', 'locale': 'es-ES', 'gender': 'female'},
      ])?['name'],
      'Z woman',
    );
  });

  for (final result in [1, 0]) {
    test('speech requests focus and handles platform result $result', () async {
      const channel = MethodChannel('flutter_tts');
      final calls = <MethodCall>[];
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
            calls.add(call);
            if (call.method == 'getLanguages') return ['es-ES'];
            if (call.method == 'getVoices') return [];
            if (call.method == 'speak') return result;
            return 1;
          });
      addTearDown(
        () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, null),
      );
      final engine = RecordingSpeechEngine(result);
      final speech = DeviceSpeech(engine: engine);
      final playback = speech.speak('hola', 'Spanish', awaitCompletion: true);
      if (result == 0) {
        await expectLater(
          playback,
          throwsA(isA<SpeechVoiceUnavailableException>()),
        );
      } else {
        await playback;
      }
      expect(engine.requestedFocus, true);
      expect(engine.spokenText, 'hola');
    });
  }

  for (final knownGender in [false, true]) {
    test(
      'selects opaque voices and retries the system voice after failure: $knownGender',
      () async {
        const channel = MethodChannel('flutter_tts');
        final calls = <MethodCall>[];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (call) async {
              calls.add(call);
              if (call.method == 'getLanguages') return ['es-MX'];
              if (call.method == 'getVoices') {
                return [
                  {
                    'name': knownGender ? 'Spanish female' : 'es-mx-x-local',
                    'locale': 'es-MX',
                  },
                ];
              }
              return 1;
            });
        addTearDown(
          () => TestDefaultBinaryMessengerBinding
              .instance
              .defaultBinaryMessenger
              .setMockMethodCallHandler(channel, null),
        );
        final engine = FailingSelectedVoiceEngine(knownGender);
        await DeviceSpeech(engine: engine)
            .speak('hola', 'Spanish', awaitCompletion: true);
        expect(
          calls.where((c) => c.method == 'setVoice').length,
          1,
        );
        expect(
          calls.where((c) => c.method == 'setLanguage').map((c) => c.arguments),
          knownGender ? ['es-MX', 'es-MX'] : ['es-MX'],
        );
        expect(engine.attempts, knownGender ? 2 : 1);
      },
    );
  }

  test('new language labels resolve to their regional speech locales', () {
    expect(preferredSpeechLocale('Polish'), 'pl-PL');
    expect(preferredSpeechLocale('Chinese (Simplified)'), 'zh-CN');
    expect(preferredSpeechLocale('Malayalam'), 'ml-IN');
    expect(preferredSpeechLocale('Norwegian'), 'nb-NO');
    expect(preferredSpeechLocale('Japanese'), 'ja-JP');
  });

  test('uses exact preferred locale when installed', () {
    expect(
      chooseBestSpeechLocale('European Spanish', ['en-US', 'es-ES', 'es-MX']),
      'es-ES',
    );
  });

  test('falls back to another installed regional voice', () {
    expect(
      chooseBestSpeechLocale('European Spanish', ['en-US', 'es_US']),
      'es-US',
    );
    expect(
      chooseBestSpeechLocale('European Portuguese', ['pt-BR', 'en-GB']),
      'pt-BR',
    );
  });

  test('reports when no voice for the language is installed', () {
    expect(chooseBestSpeechLocale('German', ['en-US', 'es-ES']), isNull);
  });

  test('uses Apple voice gender metadata and retains the identifier', () {
    final voices = [
      {
        'name': 'Monica',
        'locale': 'es_ES',
        'gender': 'VoiceGender.female',
        'identifier': 'com.apple.voice.compact.es-ES.Monica',
        'quality': 'enhanced',
      },
      {
        'name': 'Jorge',
        'locale': 'es-ES',
        'gender': 'VoiceGender.male',
        'identifier': 'com.apple.voice.compact.es-ES.Jorge',
      },
    ];
    final female = chooseBestSpeechVoice(
      'European Spanish',
      SpeechVoiceGender.female,
      voices,
    );
    final male = chooseBestSpeechVoice(
      'European Spanish',
      SpeechVoiceGender.male,
      voices,
    );

    expect(female?['name'], 'Monica');
    expect(female?['identifier'], 'com.apple.voice.compact.es-ES.Monica');
    expect(male?['name'], 'Jorge');
  });

  test('prefers the requested voice gender in the correct language', () {
    final voices = [
      {'name': 'Spanish male 1', 'locale': 'es_ES'},
      {'name': 'Spanish female 1', 'locale': 'es-ES'},
      {'name': 'English female', 'locale': 'en-US'},
    ];
    expect(
      chooseBestSpeechVoice(
        'European Spanish',
        SpeechVoiceGender.female,
        voices,
      )?['name'],
      'Spanish female 1',
    );
    expect(
      chooseBestSpeechVoice(
        'European Spanish',
        SpeechVoiceGender.male,
        voices,
      )?['name'],
      'Spanish male 1',
    );
  });
}

class RecordingSpeechEngine extends FlutterTts {
  RecordingSpeechEngine(this.result);
  final int result;
  bool? requestedFocus;
  String? spokenText;

  @override
  Future<dynamic> speak(String text, {bool focus = false}) async {
    requestedFocus = focus;
    spokenText = text;
    return result;
  }
}

class FailingSelectedVoiceEngine extends RecordingSpeechEngine {
  FailingSelectedVoiceEngine(this.failFirst) : super(1);
  final bool failFirst;
  int attempts = 0;

  @override
  Future<dynamic> speak(String text, {bool focus = false}) async {
    attempts++;
    if (failFirst && attempts == 1) return 0;
    return super.speak(text, focus: focus);
  }
}
