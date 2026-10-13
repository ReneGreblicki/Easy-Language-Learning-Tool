import 'package:easy_language_flashcards/generation/generation_settings.dart';
import 'package:easy_language_flashcards/home/selection_screens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'display names are alphabetical while saved identifiers stay stable',
    () {
      final labels = GenerationLanguage.alphabetical
          .map((l) => l.displayLabel)
          .toList();
      expect(labels, [...labels]..sort());
      expect(labels, containsAll(['Spanish', 'Portuguese']));
      expect(GenerationLanguage.europeanSpanish.label, 'European Spanish');
      expect(GenerationLanguage.europeanPortuguese.code, 'pt-PT');
    },
  );

  testWidgets(
    'selector sorts by shortened labels and returns canonical value',
    (tester) async {
      String? selected;
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) => TextButton(
              onPressed: () async {
                selected = await Navigator.push<String>(
                  context,
                  MaterialPageRoute(
                    builder: (_) => const LanguageSelectionScreen(
                      languages: [
                        'European Spanish',
                        'US English',
                        'European Portuguese',
                        'German',
                      ],
                      selectedLanguage: null,
                    ),
                  ),
                );
              },
              child: const Text('Open'),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();
      final titles = tester
          .widgetList<RadioListTile<String>>(find.byType(RadioListTile<String>))
          .map((tile) => (tile.title! as Text).data)
          .toList();
      expect(titles, ['German', 'Portuguese', 'Spanish', 'US English']);
      await tester.tap(find.text('Spanish'));
      await tester.pumpAndSettle();
      expect(selected, 'European Spanish');
    },
  );
}
