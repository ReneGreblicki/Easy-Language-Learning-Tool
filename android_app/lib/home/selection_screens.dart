import 'package:flutter/material.dart';

import '../models/deck.dart';

class LanguageSelectionScreen extends StatelessWidget {
  const LanguageSelectionScreen({
    required this.languages,
    required this.selectedLanguage,
    super.key,
  });

  final List<String> languages;
  final String? selectedLanguage;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Select a language')),
        body: RadioGroup<String>(
          groupValue: selectedLanguage,
          onChanged: (value) {
            if (value != null) Navigator.pop(context, value);
          },
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 10),
            itemCount: languages.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final language = languages[index];
              return RadioListTile<String>(
                key: Key('language-$language'),
                value: language,
                title: Text(language),
              );
            },
          ),
        ),
      );
}

class DeckSelectionScreen extends StatelessWidget {
  const DeckSelectionScreen({
    required this.language,
    required this.decks,
    required this.selectedDeckId,
    super.key,
  });

  final String language;
  final List<Deck> decks;
  final String? selectedDeckId;

  @override
  Widget build(BuildContext context) {
    final filtered = decks.where((deck) => deck.sourceLanguage == language).toList(growable: false);
    return Scaffold(
      appBar: AppBar(title: const Text('Select a deck')),
      body: filtered.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'No $language decks are available. Generate a new deck or synchronize one '
                  'from desktop.',
                  textAlign: TextAlign.center,
                ),
              ),
            )
          : RadioGroup<String>(
              groupValue: selectedDeckId,
              onChanged: (value) {
                final deck = filtered.where((item) => item.id == value).firstOrNull;
                if (deck != null) Navigator.pop(context, deck);
              },
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(vertical: 10),
                itemCount: filtered.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final deck = filtered[index];
                  return RadioListTile<String>(
                    key: Key('deck-${deck.id}'),
                    value: deck.id,
                    title: Text(deck.title),
                    subtitle: Text(
                      '${deck.cards.length} cards · '
                      '${deck.isDownloaded ? 'Downloaded' : 'Cloud'}',
                    ),
                  );
                },
              ),
            ),
    );
  }
}
