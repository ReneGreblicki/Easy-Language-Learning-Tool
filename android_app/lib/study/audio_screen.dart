import 'dart:async';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

import '../data/deck_repository.dart';
import '../models/deck.dart';
import 'study_screen.dart';

class _AudioItem {
  const _AudioItem(this.card, this.label, this.source);

  final Flashcard card;
  final String label;
  final String source;
}

class AudioStudyScreen extends StatefulWidget {
  const AudioStudyScreen({
    required this.deck,
    required this.mode,
    required this.repository,
    required this.onToggleTheme,
    super.key,
  });

  final Deck deck;
  final StudyContentMode mode;
  final DeckRepository repository;
  final VoidCallback onToggleTheme;

  @override
  State<AudioStudyScreen> createState() => _AudioStudyScreenState();
}

class _AudioStudyScreenState extends State<AudioStudyScreen> {
  final AudioPlayer _player = AudioPlayer();
  StreamSubscription<int?>? _indexSubscription;
  late final List<_AudioItem> _items;
  late final String _sessionKey;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final cards = List<Flashcard>.from(widget.deck.cards)
      ..sort((left, right) => left.rank.compareTo(right.rank));
    _items = [
      for (final card in cards) ...[
        if (widget.mode != StudyContentMode.sentences && card.wordAudioUrl != null)
          _AudioItem(card, card.foreignWord, card.wordAudioUrl!),
        if (widget.mode != StudyContentMode.words && card.sentenceAudioUrl != null)
          _AudioItem(card, card.foreignSentence, card.sentenceAudioUrl!),
      ],
    ];
    final ranks = widget.deck.cards.map((card) => card.rank);
    final firstRank = ranks.reduce((left, right) => left < right ? left : right);
    final lastRank = ranks.reduce((left, right) => left > right ? left : right);
    _sessionKey = '${widget.deck.id}:${widget.mode.name}:$firstRank-$lastRank';
    _prepare();
  }

  Future<void> _prepare() async {
    if (_items.isEmpty) {
      setState(() {
        _loading = false;
        _error = 'No desktop TTS audio is available for this selection. Upload the deck again with audio enabled.';
      });
      return;
    }
    try {
      final saved = await widget.repository.loadAudioPosition(_sessionKey);
      final initial = saved.clamp(0, _items.length - 1) as int;
      await _player.setAudioSources(
        _items
            .map((item) => AudioSource.uri(
                  item.source.startsWith('http') ? Uri.parse(item.source) : Uri.file(item.source),
                ))
            .toList(growable: false),
        initialIndex: initial,
      );
      _indexSubscription = _player.currentIndexStream.listen((index) {
        if (index != null) {
          widget.repository.saveAudioPosition(_sessionKey, index);
          if (mounted) setState(() {});
        }
      });
      if (mounted) setState(() => _loading = false);
    } catch (error) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Audio could not be loaded: $error';
        });
      }
    }
  }

  @override
  void dispose() {
    _indexSubscription?.cancel();
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final index = (_player.currentIndex ?? 0)
        .clamp(0, _items.isEmpty ? 0 : _items.length - 1) as int;
    final item = _items.isEmpty ? null : _items[index];
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deck.title),
        actions: [
          IconButton(
            tooltip: 'Switch light/dark theme',
            onPressed: widget.onToggleTheme,
            icon: const Icon(Icons.brightness_6_outlined),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: _loading
              ? const CircularProgressIndicator()
              : _error != null
                  ? Text(_error!, textAlign: TextAlign.center)
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          item!.label,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 16),
                        Text('Rank ${item.card.rank}  •  Audio ${index + 1} of ${_items.length}'),
                        const SizedBox(height: 24),
                        StreamBuilder<PlayerState>(
                          stream: _player.playerStateStream,
                          builder: (context, snapshot) {
                            final playing = snapshot.data?.playing ?? false;
                            return Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                IconButton.filledTonal(
                                  tooltip: 'Previous',
                                  onPressed: index == 0 ? null : _player.seekToPrevious,
                                  icon: const Icon(Icons.skip_previous),
                                ),
                                const SizedBox(width: 18),
                                IconButton.filled(
                                  tooltip: playing ? 'Pause' : 'Play',
                                  onPressed: playing ? _player.pause : _player.play,
                                  iconSize: 38,
                                  icon: Icon(playing ? Icons.pause : Icons.play_arrow),
                                ),
                                const SizedBox(width: 18),
                                IconButton.filledTonal(
                                  tooltip: 'Next',
                                  onPressed: index + 1 >= _items.length ? null : _player.seekToNext,
                                  icon: const Icon(Icons.skip_next),
                                ),
                              ],
                            );
                          },
                        ),
                        const SizedBox(height: 18),
                        const Text('Your position is saved automatically.'),
                      ],
                    ),
        ),
      ),
    );
  }
}
