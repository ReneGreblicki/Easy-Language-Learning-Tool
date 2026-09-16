import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('missing deck selection continues into requested activity', (tester) async {
    const deck = Deck(
      id: 'deck-1',
      title: 'Spanish deck',
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
    await tester.pumpWidget(
      MaterialApp(
        home: DeckLibrary(
          repository: MemoryDeckRepository(const [deck]),
          onToggleTheme: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Practice flashcards'));
    await tester.pumpAndSettle();

    expect(find.text('Select a deck'), findsOneWidget);
    await tester.tap(find.text('Spanish deck'));
    await tester.pumpAndSettle();
    expect(find.text('Flashcard settings'), findsOneWidget);
  });

  testWidgets('flashcard and audio settings offer phone voice gender', (tester) async {
    const deck = Deck(
      id: 'deck-voice',
      title: 'Voice deck',
      sourceLanguage: 'European Spanish',
      translationLanguage: 'US English',
      cards: [
        Flashcard(
          id: 'card-voice',
          rank: 1,
          foreignWord: 'hola',
          wordTranslation: 'hello',
          foreignSentence: 'Hola.',
          sentenceTranslation: 'Hello.',
        ),
      ],
    );
    final repository = MemoryDeckRepository(const [deck]);
    await repository.savePreferredLanguage('European Spanish');
    await repository.savePreferredDeck('European Spanish', deck.id);
    await tester.pumpWidget(
      MaterialApp(
        home: DeckLibrary(
          repository: repository,
          onToggleTheme: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Practice flashcards'));
    await tester.pumpAndSettle();

    expect(find.text('Flashcard settings'), findsOneWidget);
    expect(find.text('Phone voice'), findsOneWidget);
    expect(find.text('Female'), findsOneWidget);
  });
}
