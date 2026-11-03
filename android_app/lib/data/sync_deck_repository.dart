import 'dart:convert';
import 'dart:async';
import 'package:flutter/foundation.dart';

import '../models/deck.dart';
import 'deck_repository.dart';
import 'default_catalog.dart';
import 'local_deck_store.dart';
import 'supabase_deck_source.dart';

class SyncDeckRepository extends ChangeNotifier implements DeckRepository {
  SyncDeckRepository({required this.local, required this.cloud});

  final LocalDeckStore local;
  final SupabaseDeckSource cloud;
  final Set<String> _defaultIds = defaultDeckCatalog.map((d) => d.id).toSet();
  String _translation = 'US English';
  final Map<String, Deck> _defaults = {for (final deck in defaultDeckCatalog) deck.id: deck};
  Future<List<Deck>>? _catalogRefresh;
  DateTime? _catalogAttempt;
  DateTime? _syncRetryAfter;
  bool _closed = false;
  static const serverDeadline = Duration(seconds: 12);

  @override
  void dispose() { _closed = true; super.dispose(); }

  void _syncInBackground() {
    if (!_closed) unawaited(synchronizePendingProgress().catchError((Object _) {}));
  }

  Future<void>? _progressSync;
  bool _syncAgain = false;
  String translationFor(String source) => _translation == source
      ? (source == 'US English' ? 'European Spanish' : 'US English') : _translation;
  Future<void> setDefaultTranslation(String language) async {
    _translation = language;
    await local.saveMetadata('defaults:translation', language);
  }

  @override
  Future<List<Deck>> cloudLibrary({bool refresh = false}) async {
    _translation = await local.loadMetadata('defaults:translation') ?? 'US English';
    final downloaded = await local.downloadedDecks();
    for (final deck in downloaded) { cloud.registerDeck(deck); }
    final raw = await local.loadMetadata('library:catalog');
    final legacy = raw == null ? await local.loadMetadata('defaults:catalog') : null;
    final catalog = raw ?? legacy;
    final saved = catalog == null ? defaultDeckCatalog : (jsonDecode(catalog) as List)
      .map((row) => Deck.fromJson(Map<String, dynamic>.from(row as Map))).toList();
    for (final deck in saved.where((d) => d.isDefault)) {
      _defaults[deck.id] = deck;
      _defaultIds.add(deck.id);
    }
    final cached = {for (final deck in saved) deck.id: deck,
      for (final deck in downloaded) deck.id: deck}.values.toList();
    _syncInBackground();
    if (refresh) {
      try { return await _refreshCatalog(downloaded); } on Exception { return cached; }
    }
    if (_catalogAttempt == null || DateTime.now().difference(_catalogAttempt!) > const Duration(minutes: 1)) {
      unawaited(_refreshCatalog(downloaded).catchError((Object _) => cached));
    }
    return cached;
  }

  Future<List<Deck>> _refreshCatalog(List<Deck> downloaded) =>
    _catalogRefresh ??= _fetchCatalog(downloaded).whenComplete(() => _catalogRefresh = null);

  Future<List<Deck>> _fetchCatalog(List<Deck> downloaded) async {
    _catalogAttempt = DateTime.now();
    final remote = await (() async {
      final results = await Future.wait([cloud.fetchDefaults(), cloud.fetchCatalog()]);
      return [...results[0], ...results[1]];
    })().timeout(serverDeadline);
    if (_closed) return remote;
    for (final deck in remote.where((d) => d.isDefault)) {
      _defaults[deck.id] = deck;
      _defaultIds.add(deck.id);
    }
    final raw = jsonEncode(remote.map((d) => d.toJson()).toList());
    final previous = await local.loadMetadata('library:catalog');
    if (raw != previous) {
      await local.saveMetadata('library:catalog', raw);
      if (!_closed) notifyListeners();
    }
    final localIds = downloaded.map((d) => d.id).toSet();
    return [for (final deck in remote) deck.copyWith(isDownloaded: localIds.contains(deck.id))];
  }

  @override
  Future<List<Deck>> downloadedDecks() => local.downloadedDecks();

  @override
  Future<List<Deck>> trashedDecks() => cloud.fetchTrash();

  @override
  Future<void> download(String deckId) async {
    if (!_defaultIds.contains(deckId)) await cloud.restoreMobileDeck(deckId);
    await loadDeck(deckId, refresh: true);
  }

  @override
  Future<Deck> loadDeck(
    String deckId, {
    bool includeAudio = false,
    bool downloadAudio = false,
    bool refresh = false,
    int? fromRank,
    int? toRank,
  }) async {
    final cached = await local.loadDeck(deckId);
    final matchesTranslation = cached != null && (!cached.isDefault ||
      cached.translationLanguage == translationFor(cached.sourceLanguage));
    if (cached != null && matchesTranslation && !refresh && !downloadAudio) {
      cloud.registerDeck(cached);
      _syncInBackground();
      return cached;
    }
    final startedAt = DateTime.now().toUtc();
    Deck? deck;
    try {
      if (_defaultIds.contains(deckId)) {
        var metadata = _defaults[deckId];
        if (metadata == null) {
          final defaults = await cloud.fetchDefaults().timeout(serverDeadline);
          for (final item in defaults) { _defaults[item.id] = item; }
          metadata = _defaults[deckId];
        }
        if (metadata == null) throw StateError('Deck not found: $deckId');
        deck = await cloud.fetchDefault(deckId,
          translation: translationFor(metadata.sourceLanguage)).timeout(serverDeadline);
      } else {
        deck = await cloud.fetchDeck(deckId, includeAudio: includeAudio,
          fromRank: fromRank, toRank: toRank).timeout(serverDeadline);
      }
    } on Exception {
      if (cached == null || !matchesTranslation) rethrow;
      return cached;
    }
    if (deck == null) throw StateError('Deck not found: $deckId');
    cloud.registerDeck(deck);
    deck = await local.applyProgress(deck, pendingOnly: true, changedSince: startedAt);
    await local.saveDeck(deck, downloadAudio: downloadAudio, fetchedAt: startedAt);
    return (await local.loadDeck(deckId))!;
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
    if (!_defaultIds.contains(deckId)) {
      unawaited(cloud.markUsed(deckId).timeout(serverDeadline).catchError((Object _) {}));
    }
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
    // A label is saved before returning to the UI; connectivity cannot block it.
    unawaited(synchronizePendingProgress().catchError((Object _) {}));
  }

  @override
  Future<void> synchronizePendingProgress() {
    if (_closed || (_syncRetryAfter != null && DateTime.now().isBefore(_syncRetryAfter!))) {
      return Future.value();
    }
    _syncAgain = true;
    return _progressSync ??= _drainProgress().whenComplete(() => _progressSync = null);
  }

  Future<void> _drainProgress() async {
    do {
      _syncAgain = false;
      for (final progress in await local.pendingProgress()) {
        try {
          await cloud.saveProgress(
            progress.cardId,
            progress.rating,
            reviewCount: progress.reviewCount,
            updatedAt: progress.updatedAt,
          ).timeout(serverDeadline);
          await local.markProgressSynced(progress);
        } on Exception {
          _syncRetryAfter = DateTime.now().add(const Duration(seconds: 30));
          return; // One failed request is enough; leave the entire outbox intact.
        }
      }
    } while (_syncAgain);
  }
}
