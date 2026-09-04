import '../models/deck.dart';

abstract interface class DeckRepository {
  Future<List<Deck>> cloudLibrary();
  Future<List<Deck>> downloadedDecks();
  Future<void> download(String deckId);

  /// Removes only this Android installation's cached cards and audio.
  ///
  /// This method must never send a cloud delete or archive operation.
  Future<void> removeDownload(String deckId);

  Future<void> deleteEverywhere(String deckId);
  Future<void> saveProgress(String cardId, StudyRating rating);
}

class MemoryDeckRepository implements DeckRepository {
  MemoryDeckRepository(this._decks);

  final List<Deck> _decks;

  @override
  Future<List<Deck>> cloudLibrary() async =>
      List.unmodifiable(_decks.where((deck) => deck.deletedAt == null));

  @override
  Future<List<Deck>> downloadedDecks() async =>
      List.unmodifiable(_decks.where((deck) => deck.isDownloaded && deck.deletedAt == null));

  @override
  Future<void> download(String deckId) async {
    _replace(deckId, (deck) => deck.copyWith(isDownloaded: true));
  }

  @override
  Future<void> removeDownload(String deckId) async {
    _replace(deckId, (deck) => deck.copyWith(isDownloaded: false));
  }

  @override
  Future<void> deleteEverywhere(String deckId) async {
    _replace(deckId, (deck) => deck.copyWith(deletedAt: DateTime.now().toUtc()));
  }

  @override
  Future<void> saveProgress(String cardId, StudyRating rating) async {
    for (var deckIndex = 0; deckIndex < _decks.length; deckIndex++) {
      final deck = _decks[deckIndex];
      final cardIndex = deck.cards.indexWhere((card) => card.id == cardId);
      if (cardIndex < 0) continue;
      final cards = List<Flashcard>.from(deck.cards);
      cards[cardIndex] = cards[cardIndex].copyWith(rating: rating);
      _decks[deckIndex] = Deck(
        id: deck.id,
        title: deck.title,
        sourceLanguage: deck.sourceLanguage,
        translationLanguage: deck.translationLanguage,
        cards: cards,
        isDownloaded: deck.isDownloaded,
        deletedAt: deck.deletedAt,
      );
      return;
    }
    throw StateError('Card not found: $cardId');
  }

  void _replace(String deckId, Deck Function(Deck) update) {
    final index = _decks.indexWhere((deck) => deck.id == deckId);
    if (index < 0) {
      throw StateError('Deck not found: $deckId');
    }
    _decks[index] = update(_decks[index]);
  }
}
