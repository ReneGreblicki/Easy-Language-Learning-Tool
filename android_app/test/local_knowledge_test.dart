import 'dart:async';
import 'dart:io';
import 'package:easy_language_flashcards/data/local_deck_store.dart';
import 'package:easy_language_flashcards/data/default_catalog.dart';
import 'package:easy_language_flashcards/data/sync_deck_repository.dart';
import 'package:easy_language_flashcards/data/supabase_deck_source.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

const deck = Deck(id: 'personal', title: 'Personal', sourceLanguage: 'German',
  translationLanguage: 'US English', cards: [Flashcard(id: 'card', rank: 1,
    foreignWord: 'lernen', wordTranslation: 'learn', foreignSentence: 'Ich lerne.',
    sentenceTranslation: 'I learn.')]);

void main() {
  sqfliteFfiInit();
  late Directory directory;
  late Database db;
  late LocalDeckStore local;
  Future<Database> open() => databaseFactoryFfi.openDatabase('${directory.path}/progress.db',
    options: OpenDatabaseOptions(version: 1, onCreate: LocalDeckStore.createSchema));
  setUp(() async {
    directory = await Directory.systemTemp.createTemp('knowledge-test-');
    db = await open();
    local = LocalDeckStore(accountId: 'user', openDatabase: () async => db);
    await local.saveDeck(deck, downloadAudio: false);
  });
  tearDown(() async { await db.close(); await directory.delete(recursive: true); });

  test('labels persist across database reopen and stale deck refresh', () async {
    for (final level in KnowledgeLevel.values) {
      await local.saveProgress('card', level.rating);
      await db.close();
      db = await open();
      local = LocalDeckStore(accountId: 'user', openDatabase: () async => db);
      await local.saveDeck(deck, downloadAudio: false);
      expect((await local.downloadedDecks()).single.cards.single.rating.knowledgeLevel, level);
      expect((await local.applyProgress(deck, pendingOnly: true)).cards.single.rating, level.rating);
    }
  });

  test('a synced local label does not override newer downloaded progress', () async {
    await local.saveProgress('card', StudyRating.known);
    await local.markProgressSynced((await local.pendingProgress()).single);
    final remote = deck.copyWithCards([deck.cards.single.copyWith(rating: StudyRating.learning)]);
    await local.saveDeck(remote, downloadAudio: false);
    expect((await local.downloadedDecks()).single.cards.single.rating, StudyRating.learning);
  });

  test('a synced label survives restart without rewriting deck snapshots', () async {
    final before = (await db.query('downloaded_decks')).single['payload_json'];
    await local.saveProgress('card', StudyRating.known);
    await local.markProgressSynced((await local.pendingProgress()).single);
    expect((await db.query('downloaded_decks')).single['payload_json'], before);
    await db.close();
    db = await open();
    local = LocalDeckStore(accountId: 'user', openDatabase: () async => db);
    expect((await local.loadDeck('personal'))!.cards.single.rating, StudyRating.known);
  });

  test('cached deck opens without making any server request', () async {
    final cloud = OfflineSource();
    final repo = SyncDeckRepository(local: local, cloud: cloud);
    final loaded = await repo.loadDeck('personal').timeout(const Duration(milliseconds: 500));
    expect(loaded.cards.single.id, 'card');
    expect(cloud.requests, 0);
    await repo.synchronizePendingProgress();
    repo.dispose();
  });

  test('library returns cached content while remote catalog is stalled', () async {
    final cloud = StalledCatalog();
    final repo = SyncDeckRepository(local: local, cloud: cloud);
    final library = await repo.cloudLibrary().timeout(const Duration(milliseconds: 500));
    expect(library.any((d) => d.id == 'personal' && d.isDownloaded), true);
    cloud.defaults.complete([]);
    cloud.catalog.complete([deck.copyWithCards([])]);
    await repo.cloudLibrary(refresh: true);
    await repo.synchronizePendingProgress();
    repo.dispose();
  });

  test('default cache opens offline and never substitutes the wrong translation', () async {
    final metadata = defaultDeckCatalog.firstWhere((d) => d.sourceLanguage == 'European Spanish');
    await local.saveDeck(metadata.copyWithCards(deck.cards), downloadAudio: false);
    final cloud = OfflineSource();
    final repo = SyncDeckRepository(local: local, cloud: cloud);
    expect((await repo.loadDeck(metadata.id)).translationLanguage, 'US English');
    expect(cloud.requests, 0);
    await repo.setDefaultTranslation('French');
    await expectLater(repo.loadDeck(metadata.id), throwsA(isA<SocketException>()));
    expect(cloud.requests, 1);
    await repo.synchronizePendingProgress();
    repo.dispose();
  });

  test('a server fetch started before a newer local edit cannot erase it', () async {
    final startedAt = DateTime.now().toUtc().subtract(const Duration(days: 1));
    await local.saveProgress('card', StudyRating.known);
    await local.markProgressSynced((await local.pendingProgress()).single);
    await local.saveDeck(deck, downloadAudio: false, fetchedAt: startedAt);
    expect((await local.loadDeck('personal'))!.cards.single.rating, StudyRating.known);
  });

  test('offline outbox stops after first failure and retains all labels', () async {
    await local.saveProgress('card', StudyRating.known);
    await local.saveProgress('second', StudyRating.learning);
    final cloud = OfflineSource();
    final repo = SyncDeckRepository(local: local, cloud: cloud);
    await repo.synchronizePendingProgress();
    expect(cloud.requests, 1);
    expect(await local.pendingProgress(), hasLength(2));
    await repo.synchronizePendingProgress();
    expect(cloud.requests, 1);
    repo.dispose();
  });

  test('old sync acknowledgement cannot erase a newer pending label', () async {
    await local.saveProgress('card', KnowledgeLevel.dontKnow.rating);
    final older = (await local.pendingProgress()).single;
    await local.saveProgress('card', KnowledgeLevel.know.rating);
    await local.markProgressSynced(older);
    final pending = (await local.pendingProgress()).single;
    expect(pending.rating, StudyRating.known);
    await local.markProgressSynced(pending);
    expect(await local.pendingProgress(), isEmpty);
  });

  test('saving returns while upload is pending and stale fetch retains new label', () async {
    final cloud = ControlledSource();
    final repo = SyncDeckRepository(local: local, cloud: cloud);
    await repo.saveProgress('card', StudyRating.known);
    await cloud.started.future;
    expect(cloud.finish.isCompleted, false);
    expect((await repo.loadDeck('personal')).cards.single.rating, StudyRating.known);
    cloud.finish.complete();
    await repo.synchronizePendingProgress();
    expect(await local.pendingProgress(), isEmpty);
  });
}

class ControlledSource extends SupabaseDeckSource {
  ControlledSource() : super(SupabaseClient('https://example.supabase.co', 'anon'));
  final started = Completer<void>();
  final finish = Completer<void>();
  @override
  Future<Deck?> fetchDeck(String deckId, {bool includeAudio = false,
    int? fromRank, int? toRank}) async => deck;
  @override
  Future<void> markUsed(String deckId) async {}
  @override
  Future<void> saveProgress(String cardId, StudyRating rating,
    {required int reviewCount, required DateTime updatedAt}) async {
    if (!started.isCompleted) started.complete();
    await finish.future;
  }
}

class OfflineSource extends SupabaseDeckSource {
  OfflineSource() : super(SupabaseClient('https://example.supabase.co', 'anon'));
  int requests = 0;
  @override
  Future<Deck?> fetchDeck(String deckId, {bool includeAudio = false,
    int? fromRank, int? toRank}) async {
    requests++;
    throw const SocketException('offline');
  }
  @override
  Future<Deck> fetchDefault(String deckId, {String translation = 'US English'}) async {
    requests++;
    throw const SocketException('offline');
  }
  @override
  Future<void> saveProgress(String cardId, StudyRating rating,
    {required int reviewCount, required DateTime updatedAt}) async {
    requests++;
    throw const SocketException('offline');
  }
}

class StalledCatalog extends SupabaseDeckSource {
  StalledCatalog() : super(SupabaseClient('https://example.supabase.co', 'anon'));
  final defaults = Completer<List<Deck>>();
  final catalog = Completer<List<Deck>>();
  @override
  Future<List<Deck>> fetchDefaults() => defaults.future;
  @override
  Future<List<Deck>> fetchCatalog() => catalog.future;
}
