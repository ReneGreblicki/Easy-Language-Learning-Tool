import 'dart:convert';
import 'dart:io';

import 'package:easy_language_flashcards/generation/generation_settings.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('packaged corpus loads 5000 unique ranked words for every language',
      () async {
    final data = await rootBundle.load('assets/frequency/words.jsonl.gz');
    final text = utf8.decode(gzip.decode(data.buffer.asUint8List()));
    final rows = const LineSplitter()
        .convert(text)
        .map((line) => jsonDecode(line) as Map<String, dynamic>)
        .toList();
    expect(rows, hasLength(GenerationLanguage.values.length * 5000));
    for (final language in GenerationLanguage.values) {
      final selected = rows
          .where((row) => row['language'] == language.code)
          .toList();
      expect(selected, hasLength(5000), reason: language.label);
      expect(selected.map((row) => row['rank']),
          List.generate(5000, (index) => index + 1));
      expect(selected.map((row) => row['lemma']).toSet(), hasLength(5000));
    }
  });
}
