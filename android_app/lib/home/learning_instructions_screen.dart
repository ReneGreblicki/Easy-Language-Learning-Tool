import 'package:flutter/material.dart';

class LearningInstructionsScreen extends StatelessWidget {
  const LearningInstructionsScreen({super.key});

  static const steps = [
    (
      '1. Choose a language and goal',
      'Focus on one learning language and define a practical goal such as travel, everyday '
          'conversation, listening comprehension, or a CEFR level.',
    ),
    (
      '2. Build a high-frequency foundation',
      'Begin with a manageable 100–300 high-frequency rows at A1. Add roughly 5–10 new rows '
          'daily, then expand toward 1,000 while continuing to review older material. These are '
          'adjustable starting points, not universal optimal amounts.',
    ),
    (
      '3. Understand new rows in List',
      'Read the learning word and translation, then the learning sentence and translation. '
          'Notice the word in context, play its sound, and repeat it aloud.',
    ),
    (
      '4. Retrieve answers with Flashcards',
      'Try to recall the answer before pressing Turn. Use Words for unfamiliar meanings, '
          'Sentences for context, and Both to connect them.',
    ),
    (
      '5. Listen and repeat with Audio',
      'Listen without reading, recall the meaning, hear the translation, and repeat the '
          'learning-language item aloud. Gradually move playback toward normal speed.',
    ),
    (
      '6. Space reviews across days',
      'A practical starting sequence is later the same day, the next day, three days later, '
          'one week later, then two weeks and one month. Shorten intervals after failed recall.',
    ),
    (
      '7. Use understandable external media',
      'Choose material near your level. First follow the main meaning, then use captions or a '
          'transcript, check important recurring words, replay, and summarize.',
    ),
    (
      '8. Produce the language',
      'Say or write three to five original sentences, describe part of your day, retell a '
          'studied sentence, or summarize suitable media.',
    ),
    (
      '9. Measure functional progress',
      'Check whether you can recall meanings, recognize words in speech, understand unfamiliar '
          'sentences, produce original language, and summarize accessible media.',
    ),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Learning instructions')),
        body: ListView(
          key: const Key('learning-roadmap'),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          children: [
            Card(
              color: Theme.of(context).colorScheme.primaryContainer,
              child: const Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Repeat the cycle: List → Flashcards → Audio → spaced review → external '
                  'media → active use. Increase difficulty only when comprehension is stable.',
                ),
              ),
            ),
            const SizedBox(height: 8),
            for (final step in steps)
              Card(
                child: ExpansionTile(
                  title: Text(step.$1),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  expandedCrossAxisAlignment: CrossAxisAlignment.start,
                  children: [Text(step.$2)],
                ),
              ),
            const Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'The app currently supports manual spaced review rather than an automatic '
                'spaced-repetition schedule. Vocabulary count alone is not a comprehension score.',
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      );
}
