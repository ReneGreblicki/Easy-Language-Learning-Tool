import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('chooses activity before study settings', (tester) async {
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

    await tester.tap(find.text('Spanish deck'));
    await tester.pumpAndSettle();

    expect(find.text('Choose activity'), findsOneWidget);
    expect(find.text('Flashcards'), findsOneWidget);
    expect(find.text('Listen to audio'), findsOneWidget);
    expect(find.text('View list'), findsOneWidget);
  });
}
