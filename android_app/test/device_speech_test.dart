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
}
