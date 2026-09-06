import '../models/deck.dart';
import 'deck_repository.dart';
import 'local_deck_store.dart';
import 'supabase_deck_source.dart';

class SyncDeckRepository implements DeckRepository {
  SyncDeckRepository({required this.local, required this.cloud});

  final LocalDeckStore local;
  final SupabaseDeckSource cloud;

  @override
  Future<List<Deck>> cloudLibrary() async {
    await synchronizePendingProgress();
    final downloaded = await local.downloadedDecks();
    try {
      final remote = await cloud.fetchLibrary();
      final localById = {for (final deck in downloaded) deck.id: deck};
      return remote
          .map((deck) => localById[deck.id] ?? deck)
          .toList(growable: false);
    } on Exception {
      if (downloaded.isNotEmpty) return downloaded;
      rethrow;
    }
  }

  @override
  Future<List<Deck>> downloadedDecks() => local.downloadedDecks();

  @override
  Future<List<Deck>> trashedDecks() => cloud.fetchTrash();

  @override
  Future<void> download(String deckId) async {
    final decks = await cloud.fetchLibrary();
    final deck = decks.where((candidate) => candidate.id == deckId).firstOrNull;
    if (deck == null) throw StateError('Deck not found: $deckId');
    await local.saveDeck(deck);
  }

  @override
  Future<void> removeDownload(String deckId) => local.removeDownload(deckId);

  @override
  Future<void> deleteEverywhere(String deckId) async {
    await cloud.deleteEverywhere(deckId);
    await local.removeDownload(deckId);
  }

  @override
  Future<void> restore(String deckId) => cloud.restore(deckId);

  @override
  Future<void> saveProgress(String cardId, StudyRating rating) async {
    await local.saveProgress(cardId, rating);
    await synchronizePendingProgress();
  }

  @override
  Future<void> synchronizePendingProgress() async {
    for (final progress in await local.pendingProgress()) {
      try {
        await cloud.saveProgress(
          progress.cardId,
          progress.rating,
          reviewCount: progress.reviewCount,
          updatedAt: progress.updatedAt,
        );
        await local.markProgressSynced(progress.cardId);
      } on Exception {
        // Keep this row pending. A refresh, app restart, or later rating retries it.
      }
    }
  }
}
