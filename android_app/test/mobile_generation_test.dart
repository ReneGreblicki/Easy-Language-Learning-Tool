import 'package:easy_language_flashcards/generation/generation_settings.dart';
import 'package:easy_language_flashcards/generation/mobile_generation_service.dart';
import 'package:flutter_test/flutter_test.dart';

MobileGenerationSettings settings({
  GenerationCefrMode mode = GenerationCefrMode.single,
  int baseWords = 100,
  int extraForms = 0,
  Map<GenerationCefrLevel, int> percentages = const {},
}) =>
    MobileGenerationSettings(
      title: 'Spanish A1',
      learningLanguage: GenerationLanguage.europeanSpanish,
      translationLanguage: GenerationLanguage.usEnglish,
      baseWords: baseWords,
      extraForms: extraForms,
      questionPercentage: 20,
      pronounChange: 2,
      cefrMode: mode,
      singleLevel: GenerationCefrLevel.a1,
      gradualStart: GenerationCefrLevel.a1,
      gradualEnd: GenerationCefrLevel.b2,
      levelPercentages: percentages,
      seed: 42,
    );

void main() {
  test('applies the same 5000-row product limit as desktop', () {
    expect(settings(baseWords: 1000, extraForms: 4).finalRows, 5000);
    expect(settings(baseWords: 1001, extraForms: 4).validate(), isNotNull);
  });

  test('gradual percentages must total exactly 100', () {
    final invalid = settings(
      mode: GenerationCefrMode.gradual,
      percentages: {
        GenerationCefrLevel.a1: 25,
        GenerationCefrLevel.a2: 25,
        GenerationCefrLevel.b1: 25,
        GenerationCefrLevel.b2: 20,
      },
    );
    expect(invalid.validate(), contains('100%'));
  });

  test('planner creates one row per selected form and preserves ranking', () {
    final configured = settings(baseWords: 2, extraForms: 1);
    final tasks = buildGenerationTasks(
      configured,
      const [
        FrequencyWord(
          rank: 1,
          lemma: 'ser',
          partOfSpeech: 'verb',
          forms: ['soy', 'es'],
          translation: 'to be',
        ),
        FrequencyWord(
          rank: 2,
          lemma: 'tener',
          partOfSpeech: 'verb',
          forms: ['tengo', 'tiene'],
          translation: 'to have',
        ),
      ],
    );

    expect(tasks, hasLength(4));
    expect(tasks.map((task) => task['row_number']), [1, 2, 3, 4]);
    expect(tasks[1]['form_index'], 1);
    expect(tasks[1]['preferred_surface_form'], isNotEmpty);
  });
}
