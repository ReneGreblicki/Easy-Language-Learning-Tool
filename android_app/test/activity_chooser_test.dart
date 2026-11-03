import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/home/landing_menu.dart';
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

  testWidgets('repeated practice taps launch only one setup route', (tester) async {
    const deck = Deck(id: 'single', title: 'Single', sourceLanguage: 'German',
      translationLanguage: 'US English', cards: [Flashcard(id: 'single-card', rank: 1,
        foreignWord: 'lernen', wordTranslation: 'learn', foreignSentence: 'Ich lerne.',
        sentenceTranslation: 'I learn.')]);
    final repo = MemoryDeckRepository([deck]);
    await repo.savePreferredLanguage('German');
    await repo.savePreferredDeck('German', deck.id);
    final observer = CountingRoutes();
    await tester.pumpWidget(MaterialApp(navigatorObservers: [observer],
      home: DeckLibrary(repository: repo, onToggleTheme: () {})));
    await tester.pumpAndSettle();
    final start = tester.widget<LandingMenu>(find.byType(LandingMenu)).onFlashcards;
    start();
    start();
    await tester.pumpAndSettle();
    expect(observer.pushes, 2); // Home plus exactly one setup route.
    expect(find.text('Flashcard settings'), findsOneWidget);
  });

  for (final level in KnowledgeLevel.values) {
    testWidgets('practice filter selects only ${level.label} cards', (tester) async {
      final deck = Deck(id: 'filter-deck', title: 'Knowledge deck', sourceLanguage: 'German',
        translationLanguage: 'US English', cards: [
          for (final value in KnowledgeLevel.values) Flashcard(id: value.name,
            rank: value.index + 1, foreignWord: 'word-${value.name}', wordTranslation: 'translation',
            foreignSentence: 'sentence', sentenceTranslation: 'translation',
            rating: value == KnowledgeLevel.dontKnow ? StudyRating.newCard : value.rating),
        ]);
      final repository = MemoryDeckRepository([deck]);
      await repository.savePreferredLanguage('German');
      await repository.savePreferredDeck('German', deck.id);
      await tester.pumpWidget(MaterialApp(home: DeckLibrary(repository: repository, onToggleTheme: () {})));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Practice flashcards'));
      await tester.pumpAndSettle();
      final dropdown = find.byKey(const Key('knowledge-level-filter'));
      expect(tester.widget<DropdownButtonFormField<KnowledgeLevel>>(dropdown).onChanged, isNull);
      await tester.tap(find.text('Select knowledge level'));
      await tester.pumpAndSettle();
      expect(tester.widget<DropdownButtonFormField<KnowledgeLevel>>(dropdown).onChanged, isNotNull);
      await tester.tap(dropdown);
      await tester.pumpAndSettle();
      await tester.tap(find.text(level.label).last);
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Start'));
      await tester.tap(find.text('Start'));
      await tester.pumpAndSettle();
      expect(find.text('word-${level.name}'), findsOneWidget);
      expect(find.textContaining('Card 1 of 1'), findsOneWidget);
    });
  }

}

class CountingRoutes extends NavigatorObserver {
  int pushes = 0;
  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    pushes++;
    super.didPush(route, previousRoute);
  }
}
