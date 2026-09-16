import 'package:easy_language_flashcards/home/further_learning_screen.dart';
import 'package:easy_language_flashcards/home/learning_instructions_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('song choice hides duration', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: FurtherLearningScreen(language: 'European Spanish')),
    );
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('Media duration'), 250);
    expect(find.text('Media duration'), findsOneWidget);
    await tester.scrollUntilVisible(find.byKey(const Key('media-song')), -250);
    await tester.tap(find.byKey(const Key('media-song')));
    await tester.pumpAndSettle();
    expect(find.text('Media duration'), findsNothing);
  });

  testWidgets('learning instructions contain the full roadmap', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: LearningInstructionsScreen()),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('learning-roadmap')), findsOneWidget);
    expect(find.text('1. Choose a language and goal'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('9. Measure functional progress'),
      300,
    );
    expect(find.text('9. Measure functional progress'), findsOneWidget);
  });
}
