import 'package:easy_language_flashcards/data/deck_repository.dart';
import 'package:easy_language_flashcards/data/local_deck_store.dart';
import 'package:easy_language_flashcards/main.dart';
import 'package:easy_language_flashcards/models/deck.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Deck deck(String id, String language, {String? level}) => Deck(
  id: id, title: id, sourceLanguage: language, translationLanguage: 'US English',
  defaultLevel: level, catalogCardCount: level == 'A1' ? 400 : 300, cards: const []);

void main() {
  test('account storage is isolated', () {
    expect(LocalDeckStore(accountId: 'alice').storageName,
      isNot(LocalDeckStore(accountId: 'bob').storageName));
    expect(LocalDeckStore(accountId: 'alice').storageName,
      isNot(LocalDeckStore().storageName));
  });
  testWidgets('drawer occupies about half screen and opens settings', (tester) async {
    await tester.pumpWidget(const EasyLanguageFlashcards());
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Open navigation menu'));
    await tester.pumpAndSettle();
    expect(tester.getSize(find.byType(Drawer)).width,
      closeTo(tester.view.physicalSize.width / tester.view.devicePixelRatio * .58, 1));
    expect(find.text('Account settings'), findsOneWidget);
    expect(find.text('Log out'), findsOneWidget);
    await tester.tap(find.text('Display settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    expect(Theme.of(tester.element(find.byType(Switch))).brightness, Brightness.light);
  });
  testWidgets('A1 fallback, remembered per-language selection, defaults only in selector', (tester) async {
    final repo = MemoryDeckRepository([
      deck('German A1', 'German', level: 'A1'), deck('German B1', 'German', level: 'B1'),
      deck('French A1', 'French', level: 'A1'), deck('My French', 'French'),
    ]);
    await repo.savePreferredLanguage('German');
    await repo.savePreferredDeck('French', 'My French');
    await tester.pumpWidget(EasyLanguageFlashcards(repository: repo));
    await tester.pumpAndSettle();
    expect(find.text('German A1'), findsWidgets);
    expect(find.text('Default decks'), findsNothing);
    await tester.tap(find.text('Select a deck'));
    await tester.pumpAndSettle();
    expect(find.text('Default decks'), findsOneWidget);
    expect(tester.getTopLeft(find.text('Default decks')).dy,
      lessThan(tester.getTopLeft(find.text('My decks')).dy));
    await tester.tap(find.text('German B1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Select a language'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('French'));
    await tester.pumpAndSettle();
    expect(find.text('My French'), findsWidgets);
    await tester.tap(find.text('Select a language'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('German'));
    await tester.pumpAndSettle();
    expect(find.text('German B1'), findsWidgets);
  });
}
