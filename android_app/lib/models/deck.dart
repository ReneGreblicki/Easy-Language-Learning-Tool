enum StudyRating { newCard, learning, known, difficult }

class Flashcard {
  const Flashcard({
    required this.id,
    required this.rank,
    required this.foreignWord,
    required this.wordTranslation,
    required this.foreignSentence,
    required this.sentenceTranslation,
    this.rating = StudyRating.newCard,
    this.wordAudioUrl,
    this.sentenceAudioUrl,
  });

  final String id;
  final int rank;
  final String foreignWord;
  final String wordTranslation;
  final String foreignSentence;
  final String sentenceTranslation;
  final StudyRating rating;
  final String? wordAudioUrl;
  final String? sentenceAudioUrl;

  factory Flashcard.fromJson(Map<String, dynamic> json) => Flashcard(
        id: json['id'] as String,
        rank: json['rank'] as int,
        foreignWord: json['foreign_word'] as String,
        wordTranslation: json['word_translation'] as String,
        foreignSentence: json['foreign_sentence'] as String,
        sentenceTranslation: json['sentence_translation'] as String,
        rating: StudyRating.values.firstWhere(
          (value) => value.name == json['rating'],
          orElse: () => StudyRating.newCard,
        ),
        wordAudioUrl: json['word_audio_url'] as String?,
        sentenceAudioUrl: json['sentence_audio_url'] as String?,
      );

  Map<String, Object?> toJson() => {
        'id': id,
        'rank': rank,
        'foreign_word': foreignWord,
        'word_translation': wordTranslation,
        'foreign_sentence': foreignSentence,
        'sentence_translation': sentenceTranslation,
        'rating': rating.name,
        'word_audio_url': wordAudioUrl,
        'sentence_audio_url': sentenceAudioUrl,
      };

  Flashcard copyWith({StudyRating? rating}) => Flashcard(
        id: id,
        rank: rank,
        foreignWord: foreignWord,
        wordTranslation: wordTranslation,
        foreignSentence: foreignSentence,
        sentenceTranslation: sentenceTranslation,
        rating: rating ?? this.rating,
        wordAudioUrl: wordAudioUrl,
        sentenceAudioUrl: sentenceAudioUrl,
      );
}

class Deck {
  const Deck({
    required this.id,
    required this.title,
    required this.sourceLanguage,
    required this.translationLanguage,
    required this.cards,
    this.isDownloaded = false,
    this.deletedAt,
  });

  final String id;
  final String title;
  final String sourceLanguage;
  final String translationLanguage;
  final List<Flashcard> cards;
  final bool isDownloaded;
  final DateTime? deletedAt;

  factory Deck.fromJson(Map<String, dynamic> json) => Deck(
        id: json['id'] as String,
        title: json['title'] as String,
        sourceLanguage: json['source_language'] as String,
        translationLanguage: json['translation_language'] as String,
        cards: ((json['cards'] as List<dynamic>?) ?? const [])
            .map((item) => Flashcard.fromJson(item as Map<String, dynamic>))
            .toList(growable: false),
        deletedAt: json['deleted_at'] == null
            ? null
            : DateTime.parse(json['deleted_at'] as String),
      );

  Map<String, Object?> toJson() => {
        'id': id,
        'title': title,
        'source_language': sourceLanguage,
        'translation_language': translationLanguage,
        'cards': cards.map((card) => card.toJson()).toList(growable: false),
        'is_downloaded': isDownloaded ? 1 : 0,
        'deleted_at': deletedAt?.toIso8601String(),
      };

  Deck copyWith({bool? isDownloaded, DateTime? deletedAt}) => Deck(
        id: id,
        title: title,
        sourceLanguage: sourceLanguage,
        translationLanguage: translationLanguage,
        cards: cards,
        isDownloaded: isDownloaded ?? this.isDownloaded,
        deletedAt: deletedAt ?? this.deletedAt,
      );
}
