import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('empty library offers phone generation', (tester) async {
    await tester.pumpWidget(const EasyLanguageFlashcards());
    await tester.pumpAndSettle();

    expect(find.text('My decks'), findsOneWidget);
    expect(
      find.text('No decks yet. Generate one here or synchronize one from desktop.'),
      findsOneWidget,
    );
    expect(find.text('Generate a new deck'), findsOneWidget);
  });

  testWidgets('generation button is listed after the last deck', (tester) async {
    final repository = MemoryDeckRepository([
      const Deck(
        id: 'deck-1',
        title: 'Existing deck',
        sourceLanguage: 'German',
        translationLanguage: 'US English',
        cards: [],
      ),
    ]);
    await tester.pumpWidget(
      EasyLanguageFlashcards(repository: repository),
    );
    await tester.pumpAndSettle();

    final deckTop = tester.getTopLeft(find.text('Existing deck')).dy;
    final buttonTop = tester.getTopLeft(find.text('Generate a new deck')).dy;
    expect(buttonTop, greaterThan(deckTop));
  });
}
