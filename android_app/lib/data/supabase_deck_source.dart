import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/deck.dart';

class SupabaseDeckSource {
  SupabaseDeckSource(this.client);

  final SupabaseClient client;

  Future<List<Deck>> fetchLibrary({bool includeAudio = false}) async {
    final response = await client
        .from('decks')
        .select(
          'id,title,source_language,translation_language,deleted_at,'
          'cards(id,rank,foreign_word,word_translation,foreign_sentence,'
          'sentence_translation)',
        )
        .isFilter('deleted_at', null)
        .order('updated_at', ascending: false);
    final progressRows = await client
        .from('study_progress')
        .select('card_id,rating');
    final ratings = <String, String>{
      for (final progress in progressRows)
        progress['card_id'] as String: progress['rating'] as String,
    };
    final audioUrls = includeAudio ? await _audioUrls() : <String, Map<String, String>>{};
    return response
        .map((row) {
          final hydrated = Map<String, dynamic>.from(row);
          hydrated['cards'] = ((row['cards'] as List<dynamic>?) ?? const [])
              .map((item) {
                final card = Map<String, dynamic>.from(item as Map<String, dynamic>);
                final urls = audioUrls[card['id'] as String];
                card['word_audio_url'] = urls?['foreign_word'];
                card['sentence_audio_url'] = urls?['foreign_sentence'];
                card['rating'] = ratings[card['id'] as String] ?? 'newCard';
                return card;
              })
              .toList(growable: false);
          return Deck.fromJson(hydrated);
        })
        .toList(growable: false);
  }

  Future<Deck?> fetchDeck(
    String deckId, {
    bool includeAudio = false,
    int? fromRank,
    int? toRank,
  }) async {
    final decks = await fetchLibrary();
    final deck = decks.where((deck) => deck.id == deckId).firstOrNull;
    if (deck == null || !includeAudio) return deck;
    final selectedIds = deck.cards
        .where((card) =>
            (fromRank == null || card.rank >= fromRank) &&
            (toRank == null || card.rank <= toRank))
        .map((card) => card.id)
        .toSet();
    final urls = await _audioUrls(selectedIds);
    return deck.copyWithCards(
      deck.cards
          .map(
            (card) => card.copyWith(
              wordAudioUrl: urls[card.id]?['foreign_word'],
              sentenceAudioUrl: urls[card.id]?['foreign_sentence'],
            ),
          )
          .toList(growable: false),
    );
  }

  Future<Map<String, Map<String, String>>> _audioUrls([Set<String>? cardIds]) async {
    final audioRows = <Map<String, dynamic>>[];
    if (cardIds == null) {
      audioRows.addAll(
        (await client.from('card_audio').select('card_id,side,storage_path'))
            .cast<Map<String, dynamic>>(),
      );
    } else {
      final ids = cardIds.toList(growable: false);
      for (var start = 0; start < ids.length; start += 100) {
        final end = start + 100 < ids.length ? start + 100 : ids.length;
        audioRows.addAll(
          (await client
                  .from('card_audio')
                  .select('card_id,side,storage_path')
                  .inFilter('card_id', ids.sublist(start, end)))
              .cast<Map<String, dynamic>>(),
        );
      }
    }
    final result = <String, Map<String, String>>{};
    for (final audio in audioRows) {
      final cardId = audio['card_id'] as String;
      final side = audio['side'] as String;
      final storagePath = audio['storage_path'] as String;
      final signedUrl = await client.storage
          .from('flashcard-audio')
          .createSignedUrl(storagePath, 3600);
      result.putIfAbsent(cardId, () => <String, String>{})[side] = signedUrl;
    }
    return result;
  }

  Future<List<Deck>> fetchTrash() async {
    final response = await client
        .from('decks')
        .select(
          'id,title,source_language,translation_language,deleted_at,'
          'cards(id,rank,foreign_word,word_translation,foreign_sentence,'
          'sentence_translation)',
        )
        .not('deleted_at', 'is', null)
        .order('deleted_at', ascending: false);
    return response.map((row) => Deck.fromJson(row)).toList(growable: false);
  }

  Future<void> deleteEverywhere(String deckId) async {
    final deletedAt = DateTime.now().toUtc();
    await client
        .from('decks')
        .update({
          'deleted_at': deletedAt.toIso8601String(),
          'purge_after': deletedAt.add(const Duration(days: 30)).toIso8601String(),
        })
        .eq('id', deckId);
  }

  Future<void> restore(String deckId) async {
    await client
        .from('decks')
        .update({'deleted_at': null, 'purge_after': null})
        .eq('id', deckId);
  }

  Future<void> saveProgress(
    String cardId,
    StudyRating rating, {
    required int reviewCount,
    required DateTime updatedAt,
  }) async {
    final userId = client.auth.currentUser?.id;
    if (userId == null) throw const AuthException('Sign in is required.');
    await client.from('study_progress').upsert(
      {
        'user_id': userId,
        'card_id': cardId,
        'rating': rating == StudyRating.newCard ? 'new' : rating.name,
        'review_count': reviewCount,
        'last_reviewed_at': updatedAt.toUtc().toIso8601String(),
        'updated_at': updatedAt.toUtc().toIso8601String(),
      },
      onConflict: 'user_id,card_id',
    );
  }
}
