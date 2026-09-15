enum GenerationLanguage {
  usEnglish('en-US', 'US English'),
  europeanSpanish('es-ES', 'European Spanish'),
  german('de-DE', 'German'),
  europeanPortuguese('pt-PT', 'European Portuguese'),
  french('fr-FR', 'French'),
  italian('it-IT', 'Italian'),
  thaiScript('th-Thai-TH', 'Thai (Thai script)'),
  thaiPaiboon('th-Latn-TH', 'Thai (Paiboon romanization)');

  const GenerationLanguage(this.code, this.label);
  final String code;
  final String label;
}

enum GenerationCefrLevel { a1, a2, b1, b2, c1, c2 }

extension GenerationCefrLevelLabel on GenerationCefrLevel {
  String get label => name.toUpperCase();
}

enum GenerationCefrMode { single, gradual }

class MobileGenerationSettings {
  const MobileGenerationSettings({
    required this.title,
    required this.learningLanguage,
    required this.translationLanguage,
    required this.baseWords,
    required this.extraForms,
    required this.questionPercentage,
    required this.pronounChange,
    required this.cefrMode,
    required this.singleLevel,
    required this.gradualStart,
    required this.gradualEnd,
    required this.levelPercentages,
    required this.seed,
  });

  final String title;
  final GenerationLanguage learningLanguage;
  final GenerationLanguage translationLanguage;
  final int baseWords;
  final int extraForms;
  final int questionPercentage;
  final int pronounChange;
  final GenerationCefrMode cefrMode;
  final GenerationCefrLevel singleLevel;
  final GenerationCefrLevel gradualStart;
  final GenerationCefrLevel gradualEnd;
  final Map<GenerationCefrLevel, int> levelPercentages;
  final int seed;

  int get finalRows => baseWords * (1 + extraForms);
  int get maximumBaseWords => 5000 ~/ (1 + extraForms);

  List<GenerationCefrLevel> get selectedLevels {
    if (cefrMode == GenerationCefrMode.single) return [singleLevel];
    final levels = GenerationCefrLevel.values;
    final start = levels.indexOf(gradualStart);
    final end = levels.indexOf(gradualEnd);
    if (start > end) return const [];
    return levels.sublist(start, end + 1);
  }

  String? validate() {
    if (title.trim().isEmpty || title.trim().length > 200) {
      return 'Enter a deck name between 1 and 200 characters.';
    }
    if (learningLanguage == translationLanguage) {
      return 'Learning and translation languages must be different.';
    }
    if (baseWords < 1 || baseWords > maximumBaseWords || finalRows > 5000) {
      return 'Choose 1 to $maximumBaseWords base words for the selected number of extra forms.';
    }
    if (extraForms < 0 || extraForms > 4) {
      return 'Extra forms must be between 0 and 4.';
    }
    if (questionPercentage < 0 || questionPercentage > 100) {
      return 'Questions must be between 0% and 100%.';
    }
    if (pronounChange < 0 || pronounChange > 5) {
      return 'Pronoun change must be between 0 and 5.';
    }
    if (cefrMode == GenerationCefrMode.gradual) {
      final selected = selectedLevels;
      if (selected.isEmpty) return 'The gradual CEFR range must run from a lower to a higher level.';
      final total = selected.fold<int>(0, (sum, level) => sum + (levelPercentages[level] ?? 0));
      if (total != 100) return 'Gradual CEFR percentages must total exactly 100%.';
    }
    return null;
  }

  Map<String, Object?> toJson() => {
        'learning_language': learningLanguage.code,
        'translation_language': translationLanguage.code,
        'base_sentences': baseWords,
        'extra_forms': extraForms,
        'question_percentage': questionPercentage,
        'pronoun_change': pronounChange,
        'cefr_mode': cefrMode.name,
        'single_level': singleLevel.label,
        'gradual_start': gradualStart.label,
        'gradual_end': gradualEnd.label,
        'level_percentages': {
          for (final entry in levelPercentages.entries) entry.key.label: entry.value,
        },
        'seed': seed,
        'generated_on': 'android',
      };
}

class FrequencyWord {
  const FrequencyWord({
    required this.rank,
    required this.lemma,
    required this.partOfSpeech,
    required this.forms,
    required this.translation,
  });

  final int rank;
  final String lemma;
  final String partOfSpeech;
  final List<String> forms;
  final String translation;
}
