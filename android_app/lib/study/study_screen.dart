import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:just_audio/just_audio.dart';

import '../data/deck_repository.dart';
import '../models/deck.dart';

enum StudyContentMode { words, sentences, both }

extension StudyContentModeLabel on StudyContentMode {
  String get label => switch (this) {
        StudyContentMode.words => 'Words',
        StudyContentMode.sentences => 'Sentences',
        StudyContentMode.both => 'Words and sentences',
      };
}

class StudyScreen extends StatefulWidget {
  const StudyScreen({
    required this.deck,
    required this.repository,
    this.mode = StudyContentMode.both,
    this.onToggleTheme,
    super.key,
  });

  final Deck deck;
  final DeckRepository repository;
  final StudyContentMode mode;
  final VoidCallback? onToggleTheme;

  @override
  State<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends State<StudyScreen> {
  final AudioPlayer _audio = AudioPlayer();
  final FlutterTts _tts = FlutterTts();
  late List<Flashcard> _cards;
  var _cardIndex = 0;
  var _showingBack = false;
  var _playing = false;

  Flashcard get _card => _cards[_cardIndex];

  @override
  void initState() {
    super.initState();
    _cards = List<Flashcard>.from(widget.deck.cards);
  }

  @override
  void dispose() {
    _audio.dispose();
    _tts.stop().catchError((_) => 0);
    super.dispose();
  }

  String get _word => _showingBack ? _card.wordTranslation : _card.foreignWord;
  String get _sentence =>
      _showingBack ? _card.sentenceTranslation : _card.foreignSentence;

  List<String> get _audioUrls {
    if (_showingBack) return const [];
    return switch (widget.mode) {
      StudyContentMode.words => [_card.wordAudioUrl].nonNulls.toList(),
      StudyContentMode.sentences => [_card.sentenceAudioUrl].nonNulls.toList(),
      StudyContentMode.both =>
        [_card.wordAudioUrl, _card.sentenceAudioUrl].nonNulls.toList(),
    };
  }

  List<String> get _spokenText => switch (widget.mode) {
        StudyContentMode.words => [_word],
        StudyContentMode.sentences => [_sentence],
        StudyContentMode.both => [_word, _sentence],
      };

  String get _speechLanguage {
    final language = (_showingBack
            ? widget.deck.translationLanguage
            : widget.deck.sourceLanguage)
        .toLowerCase();
    if (language.contains('spanish')) return 'es-ES';
    if (language.contains('german')) return 'de-DE';
    if (language.contains('portuguese')) return 'pt-PT';
    if (language.contains('french')) return 'fr-FR';
    if (language.contains('italian')) return 'it-IT';
    if (language.contains('thai')) return 'th-TH';
    return 'en-US';
  }

  void _flip() => setState(() => _showingBack = !_showingBack);

  void _move(int offset) {
    final next = (_cardIndex + offset).clamp(0, _cards.length - 1);
    setState(() {
      _cardIndex = next;
      _showingBack = false;
    });
  }

  void _reshuffle() {
    final previous = _card.id;
    _cards.shuffle(Random.secure());
    if (_cards.length > 1 && _cards.first.id == previous) {
      final first = _cards.removeAt(0);
      _cards.insert(1, first);
    }
    setState(() {
      _cardIndex = 0;
      _showingBack = false;
    });
  }

  Future<void> _play() async {
    if (_playing) return;
    setState(() => _playing = true);
    try {
      await _audio.stop();
      var playedDownloadedAudio = false;
      if (_audioUrls.isNotEmpty) {
        try {
          for (final url in _audioUrls) {
            if (url.startsWith('http://') || url.startsWith('https://')) {
              await _audio.setUrl(url);
            } else {
              await _audio.setFilePath(url);
            }
            await _audio.seek(Duration.zero);
            await _audio.play();
          }
          playedDownloadedAudio = true;
        } catch (_) {
          await _audio.stop();
        }
      }
      if (!playedDownloadedAudio) {
        await _tts.awaitSpeakCompletion(true);
        await _tts.setLanguage(_speechLanguage);
        await _tts.setSpeechRate(0.42);
        await _tts.speak(_spokenText.where((text) => text.trim().isNotEmpty).join('. '));
      }
    } finally {
      if (mounted) setState(() => _playing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_cards.isEmpty) {
      return const Scaffold(body: Center(child: Text('This deck has no cards.')));
    }
    final dark = Theme.of(context).brightness == Brightness.dark;
    final cardColor = dark ? const Color(0xFF18233B) : Colors.white;
    final borderColor = dark ? const Color(0xFF334155) : const Color(0xFFD5DEEA);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.deck.title),
        actions: [
          if (widget.onToggleTheme != null)
            IconButton(
              tooltip: 'Switch light/dark theme',
              onPressed: widget.onToggleTheme,
              icon: const Icon(Icons.brightness_6_outlined),
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
              decoration: BoxDecoration(
                color: dark ? const Color(0xFF203E61) : const Color(0xFFE1EDF9),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                '${widget.deck.sourceLanguage}  →  ${widget.deck.translationLanguage}',
                style: TextStyle(
                  color: dark ? const Color(0xFF8BC7F5) : const Color(0xFF245E96),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
                child: Material(
                  color: cardColor,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                    side: BorderSide(color: borderColor),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: LayoutBuilder(
                    builder: (context, constraints) => Stack(
                      children: [
                        Positioned.fill(
                          child: InkWell(
                            key: const Key('flashcard-surface'),
                            onTap: _flip,
                            child: Padding(
                              padding: const EdgeInsets.fromLTRB(26, 20, 26, 150),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  if (widget.mode != StudyContentMode.sentences)
                                    Text(
                                      _word,
                                      textAlign: TextAlign.center,
                                      style: Theme.of(context)
                                          .textTheme
                                          .headlineLarge
                                          ?.copyWith(fontWeight: FontWeight.bold),
                                    ),
                                  if (widget.mode == StudyContentMode.both)
                                    const SizedBox(height: 28),
                                  if (widget.mode != StudyContentMode.words)
                                    Text(
                                      _sentence,
                                      textAlign: TextAlign.center,
                                      style: Theme.of(context).textTheme.headlineSmall,
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        Positioned(
                          left: 0,
                          right: 0,
                          top: constraints.maxHeight * 0.75,
                          child: Divider(height: 1, thickness: 1, color: borderColor),
                        ),
                        Positioned(
                          left: 0,
                          right: 0,
                          top: constraints.maxHeight * 0.75 - 34,
                          child: Center(
                            child: SizedBox.square(
                              dimension: 68,
                              child: IconButton(
                                key: const Key('sound-button'),
                                tooltip: 'Play this side',
                                onPressed: _playing ? null : _play,
                                style: IconButton.styleFrom(
                                  backgroundColor: cardColor,
                                  foregroundColor: dark
                                      ? const Color(0xFF8BC7F5)
                                      : const Color(0xFF245E96),
                                  side: BorderSide(
                                    width: 2,
                                    color: dark
                                        ? const Color(0xFF4EA5E0)
                                        : const Color(0xFF9CC6E8),
                                  ),
                                ),
                                iconSize: 34,
                                icon: Icon(_playing ? Icons.more_horiz : Icons.volume_up),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Text(
              'Workbook rank ${_card.rank}  •  Card ${_cardIndex + 1} of ${_cards.length}  •  '
              '${_showingBack ? 'Back' : 'Front'}',
              textAlign: TextAlign.center,
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 8, 18, 6),
              child: LinearProgressIndicator(value: (_cardIndex + 1) / _cards.length),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: _cardIndex == 0 ? null : () => _move(-1),
                      child: const Text('← Previous'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: _flip,
                      child: const Text('Turn'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: _cardIndex + 1 == _cards.length ? null : () => _move(1),
                      child: const Text('Next →'),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: FilledButton(
                onPressed: _reshuffle,
                child: const Text('↻  Reshuffle'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
