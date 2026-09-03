import '../models/deck.dart';
import 'deck_repository.dart';
import 'local_deck_store.dart';
import 'supabase_deck_source.dart';

class SyncDeckRepository implements DeckRepository {
  SyncDeckRepository({required this.local, required this.cloud});

  final LocalDeckStore local;
  final SupabaseDeckSource cloud;

  @override
  Future<List<Deck>> cloudLibrary() => cloud.fetchLibrary();

  @override
  Future<List<Deck>> downloadedDecks() => local.downloadedDecks();

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
}
