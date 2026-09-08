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
