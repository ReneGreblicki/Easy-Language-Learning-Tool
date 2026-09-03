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
  });

  final String id;
  final int rank;
  final String foreignWord;
  final String wordTranslation;
  final String foreignSentence;
  final String sentenceTranslation;
  final StudyRating rating;
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
