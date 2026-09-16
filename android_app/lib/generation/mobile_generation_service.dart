import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/services.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'generation_settings.dart';

class GenerationJob {
  const GenerationJob({
    required this.id,
    required this.deckId,
    required this.title,
    required this.sourceLanguage,
    required this.status,
    required this.completedRows,
    required this.totalRows,
    required this.createdAt,
    required this.updatedAt,
    this.errorMessage,
  });

  final String id;
  final String deckId;
  final String title;
  final String sourceLanguage;
  final String status;
  final int completedRows;
  final int totalRows;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? errorMessage;

  bool get isActive => status == 'queued' || status == 'running';

  factory GenerationJob.fromJson(Map<String, dynamic> json) => GenerationJob(
        id: json['id'] as String,
        deckId: json['deck_id'] as String,
        title: json['title'] as String,
        sourceLanguage: json['source_language'] as String,
        status: json['status'] as String,
        completedRows: json['completed_rows'] as int? ?? 0,
        totalRows: json['total_rows'] as int,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
        errorMessage: json['error_message'] as String?,
      );
}

class MobileGenerationService {
  MobileGenerationService({
    required this.client,
    this.assetPath = 'assets/frequency/words.jsonl.gz',
  });

  final SupabaseClient client;
  final String assetPath;
  List<Map<String, dynamic>>? _frequencyRows;

  Future<GenerationJob> start(MobileGenerationSettings settings) async {
    final validationError = settings.validate();
    if (validationError != null) throw FormatException(validationError);
    final words = await _selectWords(settings);
    final tasks = buildGenerationTasks(settings, words);
    final response = await client.functions.invoke(
      'generate-deck',
      body: {
        'title': settings.title.trim(),
        'learning_language': settings.learningLanguage.label,
        'learning_language_code': settings.learningLanguage.code,
        'translation_language': settings.translationLanguage.label,
        'translation_language_code': settings.translationLanguage.code,
        'settings': settings.toJson(),
        'tasks': tasks,
      },
    );
    if (response.status < 200 || response.status >= 300 || response.data is! Map) {
      throw StateError(_functionMessage(response.data));
    }
    final data = Map<String, dynamic>.from(response.data as Map);
    return GenerationJob(
      id: data['job_id'] as String,
      deckId: data['deck_id'] as String,
      title: settings.title.trim(),
      sourceLanguage: settings.learningLanguage.label,
      status: data['status'] as String? ?? 'queued',
      completedRows: 0,
      totalRows: data['total_rows'] as int? ?? tasks.length,
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
  }

  Future<List<GenerationJob>> jobs() async {
    final rows = await client
        .from('mobile_generation_jobs')
        .select('id,deck_id,title,source_language,status,completed_rows,total_rows,created_at,updated_at,error_message')
        .order('created_at', ascending: false)
        .limit(20);
    return rows.map((row) => GenerationJob.fromJson(row)).toList(growable: false);
  }

  Future<void> resume(String jobId) async {
    final response = await client.functions.invoke(
      'generate-deck',
      body: {'action': 'resume', 'job_id': jobId},
    );
    if (response.status < 200 || response.status >= 300) {
      throw StateError(_functionMessage(response.data));
    }
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
            translation: ((row['translations'] as Map<String, dynamic>?)?[
                        settings.translationLanguage.code] ??
                    '')
                .toString(),
          ),
        )
        .where((word) => word.rank >= settings.startRank)
        .toList()
      ..sort((left, right) => left.rank.compareTo(right.rank));
    if (selected.length < settings.baseWords) {
      throw StateError(
        'Only ${selected.length} ranked words are available from rank ${settings.startRank} for '
        '${settings.learningLanguage.label}.',
      );
    }
    return selected.take(settings.baseWords).toList(growable: false);
  }

  static String _functionMessage(Object? data) {
    if (data is Map && data['error'] is String) return data['error'] as String;
    return 'The generation service is temporarily unavailable.';
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
    'first_singular', 'second_singular', 'third_singular',
    'first_plural', 'second_plural', 'third_plural',
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
          (settings.pronounChange > 0 && random.nextInt(100) < settings.pronounChange * 20);
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
    for (final level in levels) level: settings.baseWords * (settings.levelPercentages[level] ?? 0) / 100,
  };
  final counts = {for (final level in levels) level: exact[level]!.floor()};
  final remainder = settings.baseWords - counts.values.fold<int>(0, (a, b) => a + b);
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
