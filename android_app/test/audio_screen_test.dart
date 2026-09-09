import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:easy_language_flashcards/study/audio_screen.dart';
import 'package:easy_language_flashcards/study/study_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const deck = Deck(
    id: 'deck-audio',
    title: 'Spanish audio',
    sourceLanguage: 'European Spanish',
    translationLanguage: 'US English',
    cards: [
      Flashcard(
        id: 'card-audio',
        rank: 1,
        foreignWord: 'hola',
        wordTranslation: 'hello',
        foreignSentence: 'Hola, ¿cómo estás?',
        sentenceTranslation: 'Hello, how are you?',
      ),
    ],
  );

  test('combined audio alternates learning and translation languages', () {
    final items = buildAudioStudySequence(deck, StudyContentMode.both);
    expect(
      items.map((item) => item.label),
      ['hola', 'hello', 'Hola, ¿cómo estás?', 'Hello, how are you?'],
    );
    expect(
      items.map((item) => item.language),
      ['European Spanish', 'US English', 'European Spanish', 'US English'],
    );
  });

  testWidgets('speed bar has labels only beside its endpoints', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: AudioStudyScreen(
          deck: deck,
          mode: StudyContentMode.both,
          repository: MemoryDeckRepository([deck]),
          onToggleTheme: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('−2×'), findsOneWidget);
    expect(find.text('2×'), findsOneWidget);
    expect(find.text('0'), findsNothing);
    expect(find.text('1×'), findsNothing);
    final slider = tester.widget<Slider>(find.byKey(const Key('audio-speed-slider')));
    expect(slider.label, isNull);
  });
}
