import 'package:easy_language_flashcards/audio/card_playback.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('cards without audio files go directly to device speech', () async {
    final spoken = <String>[];
    await playCardEntry(
      text: 'hola',
      source: null,
      playTransferred: (_) async =>
          fail('No file player should be initialized'),
      speak: (text) async => spoken.add(text),
    );
    expect(spoken, ['hola']);
  });

  test('transferred clip plays before device speech', () async {
    final played = <String>[];
    await playCardEntry(
      text: 'hola',
      source: 'cached.wav',
      playTransferred: (source) async => played.add(source),
      speak: (_) async => fail('The working clip already played'),
    );
    expect(played, ['cached.wav']);
  });

  test(
    'broken clip falls back per entry, including text without a clip',
    () async {
      final spoken = <String>[];
      for (final entry in [('hola', 'missing.wav'), ('Hola, amigo.', null)]) {
        await playCardEntry(
          text: entry.$1,
          source: entry.$2,
          playTransferred: (_) async => throw StateError('Missing clip'),
          speak: (text) async => spoken.add(text),
        );
      }
      expect(spoken, ['hola', 'Hola, amigo.']);
    },
  );
}
