import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/home/app_line_logo.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('landing page exposes every requested action', (tester) async {
    await tester.pumpWidget(const EasyLanguageFlashcards());
    await tester.pumpAndSettle();

    expect(find.text('Easy Language Learning Tool'), findsNothing);
    expect(find.byType(AppLineLogo), findsOneWidget);
    expect(find.text('Select a language'), findsOneWidget);
    expect(find.text('Select a deck'), findsOneWidget);
    expect(find.text('Generate a new deck'), findsOneWidget);
    expect(find.text('Practice flashcards'), findsOneWidget);
    expect(find.text('Practice audio'), findsOneWidget);
    expect(find.text('Practice list'), findsOneWidget);
    expect(find.text('Further learning'), findsOneWidget);
    expect(find.text('Learning instructions'), findsOneWidget);
  });

  testWidgets('deck selection is filtered by learning language', (tester) async {
    final repository = MemoryDeckRepository([
      const Deck(
        id: 'german',
        title: 'German deck',
        sourceLanguage: 'German',
        translationLanguage: 'US English',
        cards: [],
      ),
      const Deck(
        id: 'spanish',
        title: 'Spanish deck',
        sourceLanguage: 'European Spanish',
        translationLanguage: 'US English',
        cards: [],
      ),
    ]);
    await repository.savePreferredLanguage('German');
    await tester.pumpWidget(
      EasyLanguageFlashcards(repository: repository),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Select a deck'));
    await tester.pumpAndSettle();

    expect(find.text('German deck'), findsOneWidget);
    expect(find.text('Spanish deck'), findsNothing);
  });
}
