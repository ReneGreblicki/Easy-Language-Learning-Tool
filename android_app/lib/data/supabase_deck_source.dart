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
    return response
        .map((row) => Deck.fromJson(row))
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

  Future<void> saveProgress(String cardId, StudyRating rating) async {
    final userId = client.auth.currentUser?.id;
    if (userId == null) throw const AuthException('Sign in is required.');
    await client.from('study_progress').upsert(
      {
        'user_id': userId,
        'card_id': cardId,
        'rating': rating == StudyRating.newCard ? 'new' : rating.name,
        'review_count': 1,
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      },
      onConflict: 'user_id,card_id',
    );
  }
}
