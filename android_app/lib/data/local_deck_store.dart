import 'dart:convert';

import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../models/deck.dart';

class LocalDeckStore {
  LocalDeckStore({Future<Database> Function()? openDatabase})
      : _databaseFactory = openDatabase;

  final Future<Database> Function()? _databaseFactory;
  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await (_databaseFactory?.call() ?? _open());
    return _database!;
  }

  Future<Database> _open() async {
    final directory = await getApplicationDocumentsDirectory();
    return openDatabase(
      path.join(directory.path, 'easy_language_flashcards.sqlite3'),
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

  Future<void> saveDeck(Deck deck) async {
    final db = await database;
    final localDeck = deck.copyWith(isDownloaded: true);
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

  /// Deletes only local Android data. No cloud request is made here.
  Future<void> removeDownload(String deckId) async {
    final db = await database;
    await db.delete('downloaded_decks', where: 'id = ?', whereArgs: [deckId]);
  }
}
