import 'dart:convert';

import '../models/deck.dart';
import 'deck_repository.dart';
import 'local_deck_store.dart';
import 'supabase_deck_source.dart';

class SyncDeckRepository implements DeckRepository {
  SyncDeckRepository({required this.local, required this.cloud});

  final LocalDeckStore local;
  final SupabaseDeckSource cloud;
  final Set<String> _defaultIds = {};
  String _translation = 'US English';
  String translationFor(String source) => _translation == source
      ? (source == 'US English' ? 'European Spanish' : 'US English') : _translation;
  Future<void> setDefaultTranslation(String language) async {
    _translation = language;
    await local.saveMetadata('defaults:translation', language);
  }

  @override
  Future<List<Deck>> cloudLibrary() async {
    _translation = await local.loadMetadata('defaults:translation') ?? 'US English';
    await synchronizePendingProgress();
    final downloaded = await local.downloadedDecks();
    try {
      final defaults = await cloud.fetchDefaults();
      _defaultIds.addAll(defaults.map((d) => d.id));
      await local.saveMetadata('defaults:catalog', jsonEncode(defaults.map((d) => d.toJson()).toList()));
      final remote = [...defaults, ...await cloud.fetchLibrary()];
      final localById = {for (final deck in downloaded) deck.id: deck};
      return remote
          .map((deck) => deck.copyWith(isDownloaded: localById.containsKey(deck.id)))
          .toList(growable: false);
    } on Exception {
      final catalog = await local.loadMetadata('defaults:catalog');
      final defaults = catalog == null ? <Deck>[] : (jsonDecode(catalog) as List)
          .map((row) => Deck.fromJson(Map<String, dynamic>.from(row as Map))).toList();
      _defaultIds.addAll(defaults.map((d) => d.id));
      if (downloaded.isNotEmpty || defaults.isNotEmpty) {
        final byId = {for (final deck in defaults) deck.id: deck, for (final deck in downloaded) deck.id: deck};
        return byId.values.toList();
      }
      rethrow;
    }
  }

  @override
  Future<List<Deck>> downloadedDecks() => local.downloadedDecks();

  @override
  Future<List<Deck>> trashedDecks() => cloud.fetchTrash();

  @override
  Future<void> download(String deckId) async {
    if (!_defaultIds.contains(deckId)) await cloud.restoreMobileDeck(deckId);
    await loadDeck(deckId);
  }

  @override
  Future<Deck> loadDeck(
    String deckId, {
    bool includeAudio = false,
    bool downloadAudio = false,
    int? fromRank,
    int? toRank,
  }) async {
    Deck? deck;
    try {
      deck = _defaultIds.contains(deckId) ? await cloud.fetchDefault(deckId, translation: translationFor(
          (await cloud.fetchDefaults()).firstWhere((d) => d.id == deckId).sourceLanguage)) : await cloud.fetchDeck(
        deckId,
        includeAudio: includeAudio,
        fromRank: fromRank,
        toRank: toRank,
      );
    } on Exception {
      final downloaded = await local.downloadedDecks();
      deck = downloaded.where((candidate) => candidate.id == deckId).firstOrNull;
      if (deck == null || (deck.isDefault && deck.translationLanguage != translationFor(deck.sourceLanguage))) rethrow;
    }
    if (deck == null) throw StateError('Deck not found: $deckId');
    if (!_defaultIds.contains(deckId)) {
      try { await cloud.markUsed(deckId); } on Exception { /* Offline study remains available. */ }
    }
    await local.saveDeck(deck, downloadAudio: downloadAudio);
    if (!downloadAudio) return deck;
    final localDecks = await local.downloadedDecks();
    return localDecks.firstWhere((candidate) => candidate.id == deckId);
  }

  @override
  Future<int> loadAudioPosition(String sessionKey) => local.loadAudioPosition(sessionKey);

  @override
  Future<void> saveAudioPosition(String sessionKey, int position) =>
      local.saveAudioPosition(sessionKey, position);

  @override
  Future<void> createGeneratedDeck(
    Deck deck, {
    required Map<String, Object?> settings,
  }) async {
    await cloud.createDeck(deck, settings: settings);
    await local.saveDeck(deck, downloadAudio: false);
  }

  @override
  Future<String?> loadPreferredLanguage() => local.loadMetadata('home:learning-language');

  @override
  Future<void> savePreferredLanguage(String? language) =>
      local.saveMetadata('home:learning-language', language);

  @override
  Future<String?> loadPreferredDeck(String language) =>
      local.loadMetadata('home:selected-deck:${Uri.encodeComponent(language)}');

  @override
  Future<void> savePreferredDeck(String language, String? deckId) =>
      local.saveMetadata('home:selected-deck:${Uri.encodeComponent(language)}', deckId);

  @override
  Future<void> removeDownload(String deckId) async {
    await local.removeDownload(deckId);
    if (!_defaultIds.contains(deckId)) await cloud.scheduleMobileRemoval(deckId);
  }

  @override
  Future<void> markDeckUsed(String deckId) async {
    if (!_defaultIds.contains(deckId)) await cloud.markUsed(deckId);
  }

  @override
  Future<void> runMaintenance() => cloud.runMaintenance();

  @override
  Future<void> deleteEverywhere(String deckId) async {
    if (_defaultIds.contains(deckId)) throw StateError('Default decks cannot be deleted.');
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
