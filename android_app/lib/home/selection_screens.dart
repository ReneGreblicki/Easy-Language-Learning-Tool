import 'package:flutter/material.dart';

import '../models/deck.dart';
import '../generation/generation_settings.dart';

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

class DeckSelectionScreen extends StatefulWidget {
  const DeckSelectionScreen({
    required this.language,
    required this.decks,
    required this.selectedDeckId,
    this.translationLanguage,
    this.onTranslationChanged,
    super.key,
  });

  final String language;
  final List<Deck> decks;
  final String? selectedDeckId;

  final String? translationLanguage;
  final Future<void> Function(String)? onTranslationChanged;
  @override
  State<DeckSelectionScreen> createState() => _DeckSelectionScreenState();
}
class _DeckSelectionScreenState extends State<DeckSelectionScreen> {
  late String? _translation = widget.translationLanguage;
  String get language => widget.language;
  List<Deck> get decks => widget.decks;
  String? get selectedDeckId => widget.selectedDeckId;
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
              child: ListView(
                padding: const EdgeInsets.symmetric(vertical: 10),
                children: [
                  if (_translation != null) Padding(padding: const EdgeInsets.all(16),
                    child: DropdownButtonFormField<String>(
                      initialValue: _translation,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Default deck translations'),
                      items: [for (final item in GenerationLanguage.values.where((l) => l.label != language))
                        DropdownMenuItem(value: item.label, child: Text(item.label))],
                      onChanged: (value) async {
                        if (value == null) return;
                        await widget.onTranslationChanged?.call(value);
                        if (mounted) setState(() => _translation = value);
                      })),
                  for (final isDefault in [true, false]) ...[
                    Padding(padding: const EdgeInsets.fromLTRB(16, 14, 16, 8), child: Text(
                      isDefault ? 'Default decks' : 'My decks', style: Theme.of(context).textTheme.titleMedium)),
                    if (isDefault) const Padding(padding: EdgeInsets.symmetric(horizontal: 16),
                      child: Text('Included · do not count toward your 5 personal decks')),
                    for (final deck in filtered.where((d) => d.isDefault == isDefault))
                      RadioListTile<String>(
                        key: Key('deck-${deck.id}'), value: deck.id, title: Text(deck.title),
                        subtitle: Text('${deck.cardCount} cards · ${deck.isDownloaded ? 'Downloaded' : deck.isDefault && deck.contentVersion == null ? 'Content being prepared' : 'Download on first use'}'),
                      ),
                  ],
                ],
              ),
            ),
    );
  }
}
