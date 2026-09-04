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

  testWidgets('card advances through all four sides', (tester) async {
    final repository = MemoryDeckRepository([deck]);
    await tester.pumpWidget(
      MaterialApp(home: StudyScreen(deck: deck, repository: repository)),
    );

    expect(find.text('lernen'), findsOneWidget);
    await tester.tap(find.byType(Card));
    await tester.pump();
    expect(find.text('to learn'), findsOneWidget);
    await tester.tap(find.byType(Card));
    await tester.pump();
    expect(find.text('Ich lerne jeden Tag.'), findsOneWidget);
    await tester.tap(find.byType(Card));
    await tester.pump();
    expect(find.text('I learn every day.'), findsOneWidget);
  });

  testWidgets('known rating is persisted', (tester) async {
    final repository = MemoryDeckRepository([deck]);
    await tester.pumpWidget(
      MaterialApp(home: StudyScreen(deck: deck, repository: repository)),
    );

    await tester.tap(find.text('Known'));
    await tester.pump();

    expect(
      (await repository.cloudLibrary()).single.cards.single.rating,
      StudyRating.known,
    );
  });
}
