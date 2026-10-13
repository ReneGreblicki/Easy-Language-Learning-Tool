import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../models/deck.dart';

class PendingProgress {
  const PendingProgress({
    required this.cardId,
    required this.rating,
    required this.reviewCount,
    required this.updatedAt,
  });

  final String cardId;
  final StudyRating rating;
  final int reviewCount;
  final DateTime updatedAt;
}

class LocalDeckStore {
  LocalDeckStore({this.accountId, Future<Database> Function()? openDatabase})
      : _databaseFactory = openDatabase;

  final String? accountId;
  final Future<Database> Function()? _databaseFactory;

  String get storageName => accountId == null
      ? 'easy_language_flashcards.sqlite3'
      : 'account_${Uri.encodeComponent(accountId!)}.sqlite3';
  Future<Database>? _database;

  Future<Database> get database => _database ??= (_databaseFactory?.call() ?? _open());

  Future<Database> _open() async {
    final directory = await getApplicationDocumentsDirectory();
    return openDatabase(
      path.join(directory.path, storageName),
      version: 1,
      onCreate: (database, _) async {
        await database.execute('''
          CREATE TABLE downloaded_decks (
            id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
          )
        ''');
        await database.execute('''
          CREATE TABLE local_progress (
            card_id TEXT PRIMARY KEY,
            rating TEXT NOT NULL,
            review_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            sync_state TEXT NOT NULL DEFAULT 'pending'
          )
        ''');
        await database.execute('''
          CREATE TABLE sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
          )
        ''');
      },
    );
  }

  Future<List<Deck>> downloadedDecks() async {
    final db = await database;
    final rows = await db.query('downloaded_decks', orderBy: 'updated_at DESC');
    return rows
        .map(
          (row) => Deck.fromJson(
            jsonDecode(row['payload_json'] as String) as Map<String, dynamic>,
          ).copyWith(isDownloaded: true),
        )
        .toList(growable: false);
  }

  Future<void> saveDeck(Deck deck, {bool downloadAudio = true}) async {
    final db = await database;
    final existingDecks = await downloadedDecks();
    final existing = existingDecks.where((item) => item.id == deck.id).firstOrNull;
    final existingCards = {
      if (existing != null)
        for (final card in existing.cards) card.id: card,
    };
    final cards = <Flashcard>[];
    for (final card in deck.cards) {
      final cached = existingCards[card.id];
      cards.add(
        Flashcard(
          id: card.id,
          rank: card.rank,
          foreignWord: card.foreignWord,
          wordTranslation: card.wordTranslation,
          foreignSentence: card.foreignSentence,
          sentenceTranslation: card.sentenceTranslation,
          rating: card.rating,
          wordAudioUrl: downloadAudio
              ? await _cacheAudio(deck.id, card.id, 'word', card.wordAudioUrl)
              : cached?.wordAudioUrl,
          sentenceAudioUrl: downloadAudio
              ? await _cacheAudio(deck.id, card.id, 'sentence', card.sentenceAudioUrl)
              : cached?.sentenceAudioUrl,
        ),
      );
    }
    final localDeck = Deck(
      id: deck.id,
      title: deck.title,
      sourceLanguage: deck.sourceLanguage,
      translationLanguage: deck.translationLanguage,
      cards: cards,
      isDownloaded: true,
      deletedAt: deck.deletedAt,
      defaultLevel: deck.defaultLevel,
      catalogCardCount: deck.catalogCardCount,
      contentVersion: deck.contentVersion,
    );
    await db.insert(
      'downloaded_decks',
      {
        'id': deck.id,
        'payload_json': jsonEncode(localDeck.toJson()),
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<int> loadAudioPosition(String sessionKey) async {
    final db = await database;
    final rows = await db.query(
      'sync_metadata',
      columns: ['value'],
      where: 'key = ?',
      whereArgs: ['audio-session:$sessionKey'],
      limit: 1,
    );
    return rows.isEmpty ? 0 : int.tryParse(rows.single['value'] as String) ?? 0;
  }

  Future<void> saveAudioPosition(String sessionKey, int position) async {
    final db = await database;
    await db.insert(
      'sync_metadata',
      {'key': 'audio-session:$sessionKey', 'value': position.toString()},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<String?> loadMetadata(String key) async {
    final db = await database;
    final rows = await db.query(
      'sync_metadata',
      columns: ['value'],
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );
    return rows.isEmpty ? null : rows.single['value'] as String;
  }

  Future<void> saveMetadata(String key, String? value) async {
    final db = await database;
    if (value == null) {
      await db.delete('sync_metadata', where: 'key = ?', whereArgs: [key]);
      return;
    }
    await db.insert(
      'sync_metadata',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Deletes only local Android data. No cloud request is made here.
  Future<void> removeDownload(String deckId) async {
    final db = await database;
    await db.delete('downloaded_decks', where: 'id = ?', whereArgs: [deckId]);
    final directory = await getApplicationDocumentsDirectory();
    final audioDirectory = Directory(path.join(directory.path, 'audio', accountId ?? 'legacy', deckId));
    if (await audioDirectory.exists()) await audioDirectory.delete(recursive: true);
  }

  Future<String?> _cacheAudio(
    String deckId,
    String cardId,
    String side,
    String? url,
  ) async {
    if (url == null) return null;
    final directory = await getApplicationDocumentsDirectory();
    final audioDirectory = Directory(path.join(directory.path, 'audio', accountId ?? 'legacy', deckId));
    await audioDirectory.create(recursive: true);
    final destination = File(path.join(audioDirectory.path, '$cardId-$side.mp3'));
    final response = await http.get(Uri.parse(url));
    if (response.statusCode < 200 || response.statusCode >= 300 || response.bodyBytes.isEmpty) {
      throw HttpException('Could not download flashcard audio.', uri: Uri.parse(url));
    }
    await destination.writeAsBytes(response.bodyBytes, flush: true);
    return destination.path;
  }

  Future<void> saveProgress(String cardId, StudyRating rating) async {
    final db = await database;
    await db.rawInsert(
      '''
      INSERT INTO local_progress(card_id, rating, review_count, updated_at, sync_state)
      VALUES (?, ?, 1, ?, 'pending')
      ON CONFLICT(card_id) DO UPDATE SET
        rating = excluded.rating,
        review_count = local_progress.review_count + 1,
        updated_at = excluded.updated_at,
        sync_state = 'pending'
      ''',
      [cardId, rating.name, DateTime.now().toUtc().toIso8601String()],
    );
    // Keep the offline snapshot in sync with the rating shown on this device.
    for (final deck in await downloadedDecks()) {
      if (!deck.cards.any((card) => card.id == cardId)) continue;
      final updated = deck.copyWithCards(deck.cards.map((card) =>
        card.id == cardId ? card.copyWith(rating: rating) : card).toList());
      await db.update('downloaded_decks', {'payload_json': jsonEncode(updated.toJson())},
        where: 'id = ?', whereArgs: [deck.id]);
    }
  }

  Future<void> markProgressSynced(String cardId) async {
    final db = await database;
    await db.update(
      'local_progress',
      {'sync_state': 'synced'},
      where: 'card_id = ?',
      whereArgs: [cardId],
    );
  }

  Future<List<PendingProgress>> pendingProgress() async {
    final db = await database;
    final rows = await db.query(
      'local_progress',
      where: "sync_state = 'pending'",
      orderBy: 'updated_at ASC',
    );
    return rows
        .map(
          (row) => PendingProgress(
            cardId: row['card_id'] as String,
            rating: StudyRating.values.firstWhere(
              (value) => value.name == row['rating'],
              orElse: () => StudyRating.newCard,
            ),
            reviewCount: row['review_count'] as int,
            updatedAt: DateTime.parse(row['updated_at'] as String),
          ),
        )
        .toList(growable: false);
  }
}
