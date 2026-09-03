import 'package:flutter/material.dart';

import 'data/deck_repository.dart';
import 'models/deck.dart';

void main() {
  runApp(const EasyLanguageFlashcards());
}

class EasyLanguageFlashcards extends StatelessWidget {
  const EasyLanguageFlashcards({super.key});

  @override
  Widget build(BuildContext context) {
    final repository = MemoryDeckRepository(<Deck>[]);
    return MaterialApp(
      title: 'Easy Language Flashcards',
      theme: ThemeData(colorSchemeSeed: const Color(0xFF2563EB)),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorSchemeSeed: const Color(0xFF60A5FA),
      ),
      home: DeckLibrary(repository: repository),
    );
  }
}

class DeckLibrary extends StatefulWidget {
  const DeckLibrary({required this.repository, super.key});

  final DeckRepository repository;

  @override
  State<DeckLibrary> createState() => _DeckLibraryState();
}

class _DeckLibraryState extends State<DeckLibrary> {
  late Future<List<Deck>> _decks;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    _decks = widget.repository.cloudLibrary();
  }

  Future<void> _removeDownload(Deck deck) async {
    await widget.repository.removeDownload(deck.id);
    if (!mounted) return;
    setState(_refresh);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('My decks')),
        body: FutureBuilder<List<Deck>>(
          future: _decks,
          builder: (context, snapshot) {
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final decks = snapshot.data!;
            if (decks.isEmpty) {
              return const Center(
                child: Text('Generate a deck on desktop, then synchronize it here.'),
              );
            }
            return ListView.builder(
              itemCount: decks.length,
              itemBuilder: (context, index) {
                final deck = decks[index];
                return ListTile(
                  title: Text(deck.title),
                  subtitle: Text(
                    '${deck.sourceLanguage} → ${deck.translationLanguage} · '
                    '${deck.cards.length} cards',
                  ),
                  trailing: deck.isDownloaded
                      ? PopupMenuButton<String>(
                          onSelected: (value) {
                            if (value == 'remove') _removeDownload(deck);
                          },
                          itemBuilder: (_) => const [
                            PopupMenuItem(
                              value: 'remove',
                              child: Text('Remove download'),
                            ),
                          ],
                        )
                      : const Icon(Icons.cloud_download_outlined),
                );
              },
            );
          },
        ),
      );
}
