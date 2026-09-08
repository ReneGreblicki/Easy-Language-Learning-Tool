import 'package:flutter/material.dart';

import '../models/deck.dart';
import 'study_screen.dart';

class StudyListScreen extends StatelessWidget {
  const StudyListScreen({
    required this.deck,
    required this.mode,
    required this.onToggleTheme,
    super.key,
  });

  final Deck deck;
  final StudyContentMode mode;
  final VoidCallback onToggleTheme;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final foreignColor = dark ? const Color(0xFF8BC7F5) : const Color(0xFF245E96);
    final translationColor = dark ? const Color(0xFFD8E1EE) : const Color(0xFF172033);
    return Scaffold(
      appBar: AppBar(
        title: Text(deck.title),
        actions: [
          IconButton(
            tooltip: 'Switch light/dark theme',
            onPressed: onToggleTheme,
            icon: const Icon(Icons.brightness_6_outlined),
          ),
        ],
      ),
      body: ListView.separated(
        padding: const EdgeInsets.all(14),
        itemCount: deck.cards.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final card = deck.cards[index];
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Rank ${card.rank}', style: Theme.of(context).textTheme.labelMedium),
                  if (mode != StudyContentMode.sentences) ...[
                    const SizedBox(height: 8),
                    Text(
                      card.foreignWord,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: foreignColor,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 3),
                    Text(card.wordTranslation, style: TextStyle(color: translationColor)),
                  ],
                  if (mode == StudyContentMode.both) const SizedBox(height: 16),
                  if (mode != StudyContentMode.words) ...[
                    Text(
                      card.foreignSentence,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: foreignColor,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 3),
                    Text(card.sentenceTranslation, style: TextStyle(color: translationColor)),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
