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
}
