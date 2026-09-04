import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

import '../data/deck_repository.dart';
import '../models/deck.dart';

class StudyScreen extends StatefulWidget {
  const StudyScreen({
    required this.deck,
    required this.repository,
    super.key,
  });

  final Deck deck;
  final DeckRepository repository;

  @override
  State<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends State<StudyScreen> {
  final AudioPlayer _audio = AudioPlayer();
  var _cardIndex = 0;
  var _sideIndex = 0;

  Flashcard get _card => widget.deck.cards[_cardIndex];

  @override
  void dispose() {
    _audio.dispose();
    super.dispose();
  }

  String get _text => switch (_sideIndex) {
        0 => _card.foreignWord,
        1 => _card.wordTranslation,
        2 => _card.foreignSentence,
        _ => _card.sentenceTranslation,
      };

  String? get _audioUrl => switch (_sideIndex) {
        0 => _card.wordAudioUrl,
        2 => _card.sentenceAudioUrl,
        _ => null,
      };

  void _advanceSide() {
    setState(() => _sideIndex = (_sideIndex + 1) % 4);
  }

  void _move(int offset) {
    final next = (_cardIndex + offset).clamp(0, widget.deck.cards.length - 1);
    setState(() {
      _cardIndex = next;
      _sideIndex = 0;
    });
  }

  Future<void> _play() async {
    final url = _audioUrl;
    if (url == null) return;
    await _audio.stop();
    await _audio.setUrl(url);
    await _audio.seek(Duration.zero);
    await _audio.play();
  }

  Future<void> _rate(StudyRating rating) async {
    await widget.repository.saveProgress(_card.id, rating);
    if (_cardIndex + 1 < widget.deck.cards.length) _move(1);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.deck.cards.isEmpty) {
      return const Scaffold(body: Center(child: Text('This deck has no cards.')));
    }
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deck.title),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(4),
          child: LinearProgressIndicator(
            value: (_cardIndex + 1) / widget.deck.cards.length,
          ),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Card ${_cardIndex + 1} of ${widget.deck.cards.length} · '
                'Side ${_sideIndex + 1} of 4',
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: InkWell(
                  borderRadius: BorderRadius.circular(24),
                  onTap: _advanceSide,
                  child: Card(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Text(
                          _text,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            if (_audioUrl != null)
              IconButton.filledTonal(
                tooltip: 'Play audio',
                onPressed: _play,
                icon: const Icon(Icons.volume_up),
              ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Wrap(
                spacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: () => _rate(StudyRating.difficult),
                    child: const Text('Difficult'),
                  ),
                  OutlinedButton(
                    onPressed: () => _rate(StudyRating.learning),
                    child: const Text('Learning'),
                  ),
                  FilledButton(
                    onPressed: () => _rate(StudyRating.known),
                    child: const Text('Known'),
                  ),
                ],
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  tooltip: 'Previous card',
                  onPressed: _cardIndex == 0 ? null : () => _move(-1),
                  icon: const Icon(Icons.arrow_back),
                ),
                IconButton(
                  tooltip: 'Next card',
                  onPressed: _cardIndex + 1 == widget.deck.cards.length
                      ? null
                      : () => _move(1),
                  icon: const Icon(Icons.arrow_forward),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
