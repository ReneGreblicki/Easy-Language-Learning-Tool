import 'dart:async';
import 'dart:io';
import 'package:easy_language_flashcards/data/local_deck_store.dart';
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
