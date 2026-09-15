import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

import '../data/deck_repository.dart';
import '../models/deck.dart';
import 'generation_settings.dart';

typedef GenerationProgress = void Function(int completed, int total);

class MobileGenerationService {
  MobileGenerationService({
    required this.client,
    required this.repository,
    this.assetPath = 'assets/frequency/words.jsonl.gz',
  });

  final SupabaseClient client;
  final DeckRepository repository;
  final String assetPath;
  List<Map<String, dynamic>>? _frequencyRows;

  Future<Deck> generate(
    MobileGenerationSettings settings, {
    GenerationProgress? onProgress,
  }) async {
    final validationError = settings.validate();
    if (validationError != null) throw FormatException(validationError);
    final words = await _selectWords(settings);
    final tasks = buildGenerationTasks(settings, words);
    final generated = <Map<String, dynamic>>[];

    for (var start = 0; start < tasks.length; start += 20) {
      final end = min(start + 20, tasks.length);
      final batch = tasks.sublist(start, end);
      final response = await _invokeWithRetry(settings, batch);
      generated.addAll(response);
      onProgress?.call(generated.length, tasks.length);
    }

    generated.sort(
      (left, right) => (left['row_number'] as int).compareTo(right['row_number'] as int),
    );
    if (generated.length != tasks.length) {
      throw StateError('Generation returned an incomplete deck. No deck was saved.');
    }

    const uuid = Uuid();
    final deck = Deck(
      id: uuid.v4(),
      title: settings.title.trim(),
      sourceLanguage: settings.learningLanguage.label,
      translationLanguage: settings.translationLanguage.label,
      isDownloaded: true,
      cards: [
        for (final row in generated)
          Flashcard(
            id: uuid.v4(),
            rank: row['row_number'] as int,
            foreignWord: _requiredText(row, 'foreign_word'),
            wordTranslation: _requiredText(row, 'word_translation'),
            foreignSentence: _requiredText(row, 'foreign_sentence'),
            sentenceTranslation: _requiredText(row, 'sentence_translation'),
          ),
      ],
    );
    await repository.createGeneratedDeck(deck, settings: settings.toJson());
    return deck;
  }

  Future<List<Map<String, dynamic>>> _loadRows() async {
    if (_frequencyRows != null) return _frequencyRows!;
    final data = await rootBundle.load(assetPath);
    final decoded = utf8.decode(gzip.decode(data.buffer.asUint8List()));
    _frequencyRows = const LineSplitter()
        .convert(decoded)
        .where((line) => line.trim().isNotEmpty)
        .map((line) => jsonDecode(line) as Map<String, dynamic>)
        .toList(growable: false);
    return _frequencyRows!;
  }

  Future<List<FrequencyWord>> _selectWords(MobileGenerationSettings settings) async {
    final rows = await _loadRows();
    final selected = rows
        .where((row) => row['language'] == settings.learningLanguage.code)
        .map(
          (row) => FrequencyWord(
            rank: row['rank'] as int,
            lemma: row['lemma'] as String,
            partOfSpeech: (row['part_of_speech'] as String?) ?? 'unknown',
            forms: ((row['forms'] as List<dynamic>?) ?? const [])
                .map((value) => value.toString())
                .toList(growable: false),
            translation:
                ((row['translations'] as Map<String, dynamic>?)?[
                            settings.translationLanguage.code] ??
                        '')
                    .toString(),
          ),
        )
        .toList()
      ..sort((left, right) => left.rank.compareTo(right.rank));
    if (selected.length < settings.baseWords) {
      throw StateError(
        'Only ${selected.length} ranked words are available for '
        '${settings.learningLanguage.label}.',
      );
    }
    return selected.take(settings.baseWords).toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> _invokeWithRetry(
    MobileGenerationSettings settings,
    List<Map<String, Object?>> tasks,
  ) async {
    Object? lastError;
    for (var attempt = 0; attempt < 3; attempt++) {
      try {
        final response = await client.functions.invoke(
          'generate-deck',
          body: {
            'learning_language': settings.learningLanguage.label,
            'learning_language_code': settings.learningLanguage.code,
            'translation_language': settings.translationLanguage.label,
            'translation_language_code': settings.translationLanguage.code,
            'tasks': tasks,
          },
        );
        if (response.status < 200 || response.status >= 300) {
          throw StateError(_functionMessage(response.data));
        }
        final data = response.data;
        if (data is! Map || data['rows'] is! List) {
          throw const FormatException('The generation service returned an invalid response.');
        }
        final rows = (data['rows'] as List)
            .map((row) => Map<String, dynamic>.from(row as Map))
            .toList(growable: false);
        final expected = tasks.map((task) => task['row_number']).toSet();
        final returned = rows.map((row) => row['row_number']).toSet();
        if (rows.length != tasks.length || !returned.containsAll(expected)) {
          throw const FormatException('The generation service returned an incomplete batch.');
        }
        return rows;
      } catch (error) {
        lastError = error;
        if (attempt < 2) {
          await Future<void>.delayed(Duration(seconds: attempt + 1));
        }
      }
    }
    throw StateError(
      'Deck generation could not complete after three attempts. '
      '${lastError ?? 'Try again later.'}',
    );
  }

  static String _functionMessage(Object? data) {
    if (data is Map && data['error'] is String) return data['error'] as String;
    return 'The generation service is temporarily unavailable.';
  }

  static String _requiredText(Map<String, dynamic> row, String key) {
    final value = row[key]?.toString().trim() ?? '';
    if (value.isEmpty) throw FormatException('Generated row is missing $key.');
    return value;
  }
}

List<Map<String, Object?>> buildGenerationTasks(
  MobileGenerationSettings settings,
  List<FrequencyWord> words,
) {
  final levels = _levelSchedule(settings);
  final questionCount = (settings.baseWords * settings.questionPercentage / 100).round();
  final random = Random(settings.seed);
  const people = [
    'first_singular',
    'second_singular',
    'third_singular',
    'first_plural',
    'second_plural',
    'third_plural',
  ];
  final tasks = <Map<String, Object?>>[];
  for (var baseIndex = 0; baseIndex < words.length; baseIndex++) {
    final word = words[baseIndex];
    final alternatives = word.forms
        .where((form) => form.trim().isNotEmpty && form.toLowerCase() != word.lemma.toLowerCase())
        .toSet()
        .toList()
      ..sort();
    alternatives.shuffle(Random(settings.seed + word.rank));
    for (var formIndex = 0; formIndex <= settings.extraForms; formIndex++) {
      final changed = settings.pronounChange == 5 ||
          (settings.pronounChange > 0 &&
              random.nextInt(100) < settings.pronounChange * 20);
      tasks.add({
        'row_number': tasks.length + 1,
        'lemma': word.lemma,
        'part_of_speech': word.partOfSpeech,
        'known_forms': word.forms,
        'preferred_surface_form':
            formIndex > 0 && formIndex - 1 < alternatives.length ? alternatives[formIndex - 1] : '',
        'baseline_translation': word.translation,
        'cefr': levels[baseIndex].label,
        'sentence_kind': baseIndex < questionCount ? 'question' : 'statement',
        'grammatical_person': changed ? people[random.nextInt(people.length)] : 'neutral',
        'form_index': formIndex,
      });
    }
  }
  return tasks;
}

List<GenerationCefrLevel> _levelSchedule(MobileGenerationSettings settings) {
  if (settings.cefrMode == GenerationCefrMode.single) {
    return List.filled(settings.baseWords, settings.singleLevel);
  }
  final levels = settings.selectedLevels;
  final exact = {
    for (final level in levels)
      level: settings.baseWords * (settings.levelPercentages[level] ?? 0) / 100,
  };
  final counts = {for (final level in levels) level: exact[level]!.floor()};
  var remainder = settings.baseWords - counts.values.fold<int>(0, (a, b) => a + b);
  final order = List<GenerationCefrLevel>.from(levels)
    ..sort((a, b) {
      final af = exact[a]! - exact[a]!.floor();
      final bf = exact[b]! - exact[b]!.floor();
      return bf.compareTo(af);
    });
  for (var index = 0; index < remainder; index++) {
    counts[order[index % order.length]] = counts[order[index % order.length]]! + 1;
  }
  return [
    for (final level in levels)
      for (var index = 0; index < counts[level]!; index++) level,
  ];
}
