import 'package:easy_language_flashcards/audio/device_speech.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
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
