import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/deck.dart';

class SupabaseDeckSource {
  SupabaseDeckSource(this.client);

  final SupabaseClient client;

  Future<List<Deck>> fetchLibrary() async {
    final response = await client
        .from('decks')
        .select(
          'id,title,source_language,translation_language,deleted_at,'
          'cards(id,rank,foreign_word,word_translation,foreign_sentence,'
          'sentence_translation)',
        )
        .isFilter('deleted_at', null)
        .order('updated_at', ascending: false);
    final audioRows = await client
        .from('card_audio')
        .select('card_id,side,storage_path');
    final progressRows = await client
        .from('study_progress')
        .select('card_id,rating');
    final ratings = <String, String>{
      for (final progress in progressRows)
        progress['card_id'] as String: progress['rating'] as String,
    };
    final audioUrls = <String, Map<String, String>>{};
    for (final audio in audioRows) {
      final cardId = audio['card_id'] as String;
      final side = audio['side'] as String;
      final storagePath = audio['storage_path'] as String;
      final signedUrl = await client.storage
          .from('flashcard-audio')
          .createSignedUrl(storagePath, 3600);
      audioUrls.putIfAbsent(cardId, () => <String, String>{})[side] = signedUrl;
    }
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
