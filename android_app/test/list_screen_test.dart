import 'package:easy_language_flashcards/models/deck.dart';
import 'package:easy_language_flashcards/study/list_screen.dart';
import 'package:easy_language_flashcards/study/study_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const deck = Deck(
    id: 'deck-1',
    title: 'Spanish',
    sourceLanguage: 'European Spanish',
    translationLanguage: 'US English',
    cards: [
      Flashcard(
        id: 'card-1',
        rank: 1,
        foreignWord: 'de',
        wordTranslation: 'of; from',
        foreignSentence: '¿De quién es?',
        sentenceTranslation: 'Whose is it?',
      ),
    ],
  );

  testWidgets('combined list keeps each translation directly below its source', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: StudyListScreen(
          deck: deck,
          mode: StudyContentMode.both,
          onToggleTheme: () {},
        ),
      ),
    );

    expect(find.text('de'), findsOneWidget);
    expect(find.text('of; from'), findsOneWidget);
    expect(find.text('¿De quién es?'), findsOneWidget);
    expect(find.text('Whose is it?'), findsOneWidget);
    final source = tester.widget<Text>(find.text('de'));
    final translation = tester.widget<Text>(find.text('of; from'));
    expect(source.style?.color, isNot(translation.style?.color));
    final scrollbar = tester.widget<Scrollbar>(find.byType(Scrollbar));
    expect(scrollbar.thumbVisibility, isFalse);
    expect(scrollbar.interactive, isTrue);
  });
}
