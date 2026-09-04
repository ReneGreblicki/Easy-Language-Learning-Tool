import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('remove download keeps deck in cloud library', () async {
    final deck = Deck(
      id: 'deck-1',
      title: 'German A1',
      sourceLanguage: 'German',
      translationLanguage: 'US English',
      cards: const [],
      isDownloaded: true,
    );
    final repository = MemoryDeckRepository([deck]);

    await repository.removeDownload(deck.id);

    expect(await repository.downloadedDecks(), isEmpty);
    expect(await repository.cloudLibrary(), hasLength(1));
    expect((await repository.cloudLibrary()).single.deletedAt, isNull);
  });

  test('delete everywhere hides cloud deck', () async {
    final deck = Deck(
      id: 'deck-1',
      title: 'German A1',
      sourceLanguage: 'German',
      translationLanguage: 'US English',
      cards: const [],
    );
    final repository = MemoryDeckRepository([deck]);

    await repository.deleteEverywhere(deck.id);

    expect(await repository.cloudLibrary(), isEmpty);
  });

  test('study rating is stored without deleting the deck', () async {
    const card = Flashcard(
      id: 'card-1',
      rank: 1,
      foreignWord: 'lernen',
      wordTranslation: 'to learn',
      foreignSentence: 'Ich lerne jeden Tag.',
      sentenceTranslation: 'I learn every day.',
    );
    final repository = MemoryDeckRepository([
      const Deck(
        id: 'deck-1',
        title: 'German A1',
        sourceLanguage: 'German',
        translationLanguage: 'US English',
        cards: [card],
      ),
    ]);

    await repository.saveProgress(card.id, StudyRating.known);

    final saved = (await repository.cloudLibrary()).single.cards.single;
    expect(saved.rating, StudyRating.known);
    expect(await repository.cloudLibrary(), hasLength(1));
  });
}
