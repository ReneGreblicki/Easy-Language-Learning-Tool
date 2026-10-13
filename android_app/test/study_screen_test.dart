import 'package:easy_language_flashcards/audio/device_speech.dart';
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
      MaterialApp(
        home: StudyScreen(deck: deck, repository: repository),
      ),
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
      MaterialApp(
        home: StudyScreen(deck: deck, repository: repository),
      ),
    );

    expect(find.text('← Previous'), findsOneWidget);
    expect(find.text('Turn'), findsOneWidget);
    expect(find.text('Next →'), findsOneWidget);
    expect(find.text('↻  Reshuffle'), findsOneWidget);
    expect(find.byKey(const Key('sound-button')), findsOneWidget);
    final sound = tester.widget<IconButton>(
      find.byKey(const Key('sound-button')),
    );
    expect(sound.onPressed, isNotNull);
    expect(find.byType(Divider), findsNothing);
  });

  testWidgets(
    'sound button speaks both sides and replays without file-player setup',
    (tester) async {
      final speech = RecordingCardSpeech();
      await tester.pumpWidget(
        MaterialApp(
          home: StudyScreen(
            deck: deck,
            repository: MemoryDeckRepository([deck]),
            speech: speech,
          ),
        ),
      );
      await tester.tap(find.byKey(const Key('sound-button')));
      await tester.pumpAndSettle();
      expect(speech.entries, [
        ('lernen', 'German'),
        ('Ich lerne jeden Tag.', 'German'),
      ]);
      await tester.tap(find.byKey(const Key('sound-button')));
      await tester.pumpAndSettle();
      expect(speech.entries.length, 4);
      await tester.tap(find.byKey(const Key('flashcard-surface')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('sound-button')));
      await tester.pumpAndSettle();
      expect(speech.entries.skip(4), [
        ('to learn', 'US English'),
        ('I learn every day.', 'US English'),
      ]);
      expect(find.byType(SnackBar), findsNothing);
    },
  );

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

class RecordingCardSpeech extends DeviceSpeech {
  final entries = <(String, String)>[];

  @override
  Future<void> speak(
    String text,
    String language, {
    bool awaitCompletion = false,
    SpeechVoiceGender gender = SpeechVoiceGender.female,
    double speedFactor = 1,
  }) async {
    entries.add((text, language));
  }

  @override
  Future<void> stop() async {}
}
