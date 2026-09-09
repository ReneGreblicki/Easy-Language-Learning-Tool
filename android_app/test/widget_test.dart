import 'package:easy_language_flashcards/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('empty library explains how to obtain a deck', (tester) async {
    await tester.pumpWidget(const EasyLanguageFlashcards());
    await tester.pumpAndSettle();

    expect(find.text('My decks'), findsOneWidget);
    expect(
      find.text('Generate a deck on desktop, then synchronize it here.'),
      findsOneWidget,
    );
  });
}
