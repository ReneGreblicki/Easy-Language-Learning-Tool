import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:easy_language_flashcards/study/study_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const card = Flashcard(
    id: 'card-1',
    rank: 1,
    foreignWord: 'lernen',
    wordTranslation: 'to learn',
    foreignSentence: 'Ich lerne jeden Tag.',
    sentenceTranslation: 'I learn every day.',
  );
  const deck = Deck(
    id: 'deck-1',
    title: 'German A1',
    sourceLanguage: 'German',
    translationLanguage: 'US English',
    cards: [card],
    isDownloaded: true,
  );

  testWidgets('card flips between matching front and back', (tester) async {
    final repository = MemoryDeckRepository([deck]);
    await tester.pumpWidget(
      MaterialApp(home: StudyScreen(deck: deck, repository: repository)),
    );

    expect(find.text('lernen'), findsOneWidget);
    expect(find.text('Ich lerne jeden Tag.'), findsOneWidget);
    await tester.tap(find.byKey(const Key('flashcard-surface')));
    await tester.pump();
    expect(find.text('to learn'), findsOneWidget);
    expect(find.text('I learn every day.'), findsOneWidget);
  });

  testWidgets('offers the desktop navigation controls', (tester) async {
    final repository = MemoryDeckRepository([deck]);
    await tester.pumpWidget(
      MaterialApp(home: StudyScreen(deck: deck, repository: repository)),
    );

    expect(find.text('← Previous'), findsOneWidget);
    expect(find.text('Reveal'), findsOneWidget);
    expect(find.text('Next →'), findsOneWidget);
    expect(find.text('↻  Reshuffle'), findsOneWidget);
    expect(find.byKey(const Key('sound-button')), findsOneWidget);
  });

  testWidgets('words mode hides sentence content', (tester) async {
    final repository = MemoryDeckRepository([deck]);
    await tester.pumpWidget(
      MaterialApp(
        home: StudyScreen(
          deck: deck,
          repository: repository,
          mode: StudyContentMode.words,
        ),
      ),
    );

    expect(find.text('lernen'), findsOneWidget);
    expect(find.text('Ich lerne jeden Tag.'), findsNothing);
  });
}
