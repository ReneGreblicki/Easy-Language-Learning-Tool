import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

import '../audio/device_speech.dart';
import '../data/deck_repository.dart';
import '../errors/app_error.dart';
import '../models/deck.dart';
import 'study_screen.dart';

class _AudioItem {
  const _AudioItem(this.card, this.label, this.source);

  final Flashcard card;
  final String label;
  final String? source;
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
  final DeviceSpeech _speech = DeviceSpeech();
  late final List<_AudioItem> _items;
  late final String _sessionKey;
  bool _loading = true;
  bool _playing = false;
  int _index = 0;
  int _playbackGeneration = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    final cards = List<Flashcard>.from(widget.deck.cards)
      ..sort((left, right) => left.rank.compareTo(right.rank));
    _items = [
      for (final card in cards) ...[
        if (widget.mode != StudyContentMode.sentences && card.foreignWord.trim().isNotEmpty)
          _AudioItem(card, card.foreignWord, card.wordAudioUrl),
        if (widget.mode != StudyContentMode.words && card.foreignSentence.trim().isNotEmpty)
          _AudioItem(card, card.foreignSentence, card.sentenceAudioUrl),
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
        _error = 'There are no words or sentences in this selection.';
      });
      return;
    }
    try {
      final saved = await widget.repository.loadAudioPosition(_sessionKey);
      if (!mounted) return;
      setState(() {
        _index = saved.clamp(0, _items.length - 1);
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = describeAppError(
          error,
          fallback: 'Your saved audio position could not be loaded. Reopen the deck and try again.',
        );
      });
    }
  }

  Future<void> _playSource(String source) async {
    if (source.startsWith('http://') || source.startsWith('https://')) {
      await _player.setUrl(source).timeout(const Duration(seconds: 10));
    } else {
      await _player.setFilePath(source).timeout(const Duration(seconds: 10));
    }
    await _player.seek(Duration.zero);
    await _player.play().timeout(const Duration(minutes: 3));
  }

  Future<void> _playItem(_AudioItem item) async {
    if (item.source != null && item.source!.isNotEmpty) {
      try {
        await _playSource(item.source!);
        return;
      } catch (_) {
        await _player.stop();
      }
    }
    await _speech.speak(
      item.label,
      widget.deck.sourceLanguage,
      awaitCompletion: true,
    );
  }

  Future<void> _play() async {
    if (_playing) {
      await _stop();
      return;
    }
    final generation = ++_playbackGeneration;
    setState(() {
      _playing = true;
      _error = null;
    });
    try {
      while (mounted && generation == _playbackGeneration && _index < _items.length) {
        await _playItem(_items[_index]);
        if (!mounted || generation != _playbackGeneration) return;
        if (_index + 1 >= _items.length) break;
        setState(() => _index += 1);
        await widget.repository.saveAudioPosition(_sessionKey, _index);
      }
    } catch (error) {
      if (mounted && generation == _playbackGeneration) {
        setState(() {
          _error = describeAppError(
            error,
            fallback: error.toString().replaceFirst('Exception: ', ''),
          );
        });
      }
    } finally {
      if (mounted && generation == _playbackGeneration) {
        setState(() => _playing = false);
      }
    }
  }

  Future<void> _stop() async {
    _playbackGeneration += 1;
    await _player.stop();
    await _speech.stop();
    if (mounted) setState(() => _playing = false);
  }

  Future<void> _move(int offset) async {
    await _stop();
    final next = (_index + offset).clamp(0, _items.length - 1);
    setState(() {
      _index = next;
      _error = null;
    });
    await widget.repository.saveAudioPosition(_sessionKey, next);
  }

  @override
  void dispose() {
    _playbackGeneration += 1;
    _player.dispose();
    _speech.stop().catchError((_) {});
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final item = _items.isEmpty ? null : _items[_index];
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
              : item == null
                  ? Text(_error!, textAlign: TextAlign.center)
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          item.label,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 16),
                        Text('Rank ${item.card.rank}  •  Audio ${_index + 1} of ${_items.length}'),
                        if (_error != null) ...[
                          const SizedBox(height: 18),
                          Text(
                            _error!,
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Theme.of(context).colorScheme.error),
                          ),
                        ],
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            IconButton.filledTonal(
                              tooltip: 'Previous',
                              onPressed: _index == 0 ? null : () => _move(-1),
                              icon: const Icon(Icons.skip_previous),
                            ),
                            const SizedBox(width: 18),
                            IconButton.filled(
                              tooltip: _playing ? 'Stop' : 'Play',
                              onPressed: _play,
                              iconSize: 38,
                              icon: Icon(_playing ? Icons.stop : Icons.play_arrow),
                            ),
                            const SizedBox(width: 18),
                            IconButton.filledTonal(
                              tooltip: 'Next',
                              onPressed: _index + 1 >= _items.length ? null : () => _move(1),
                              icon: const Icon(Icons.skip_next),
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        const Text(
                          'Transferred desktop audio is used when available. '
                          'Otherwise, the phone voice is used. Your position is saved automatically.',
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
        ),
      ),
    );
  }
}
