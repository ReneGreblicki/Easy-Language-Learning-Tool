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

    final scrollable = find.byType(Scrollable).first;
    await tester.scrollUntilVisible(
      find.text('Media duration'),
      250,
      scrollable: scrollable,
    );
    expect(find.text('Media duration'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('media-song')),
      -250,
      scrollable: scrollable,
    );
    await tester.tap(find.byKey(const Key('media-song')));
    await tester.pumpAndSettle();
    expect(find.text('Media duration'), findsNothing);
  });

  testWidgets('movie hides duration and series names episode duration', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: FurtherLearningScreen(language: 'European Spanish')),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('media-movie')));
    await tester.pumpAndSettle();
    expect(find.text('Media duration'), findsNothing);

    await tester.tap(find.byKey(const Key('media-series')));
    await tester.pumpAndSettle();
    expect(find.text('Episode duration'), findsOneWidget);
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
