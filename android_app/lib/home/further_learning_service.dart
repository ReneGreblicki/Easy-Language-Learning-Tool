import 'package:supabase_flutter/supabase_flutter.dart';

class MediaRecommendation {
  const MediaRecommendation({
    required this.title,
    required this.description,
    required this.url,
    this.imageUrl,
  });

  final String title;
  final String description;
  final String url;
  final String? imageUrl;

  factory MediaRecommendation.fromJson(Map<String, dynamic> json) => MediaRecommendation(
        title: json['title'] as String,
        description: json['description'] as String,
        url: json['url'] as String,
        imageUrl: json['image_url'] as String?,
      );
}

class FurtherLearningService {
  const FurtherLearningService(this.client);

  final SupabaseClient client;

  Future<List<MediaRecommendation>> recommend({
    required String language,
    required String media,
    required String genre,
    required String level,
    String? duration,
  }) async {
    final response = await client.functions.invoke(
      'recommend-media',
      body: {
        'language': language,
        'media': media,
        'genre': genre,
        'level': level,
        if (duration != null) 'duration': duration,
      },
    );
    if (response.status < 200 || response.status >= 300 || response.data is! Map) {
      final data = response.data;
      final message = data is Map && data['error'] is String
          ? data['error'] as String
          : 'Suitable media could not be found right now.';
      throw StateError(message);
    }
    final results = (response.data as Map)['results'];
    if (results is! List || results.length != 3) {
      throw const FormatException('The recommendation service did not return three options.');
    }
    return results
        .map((item) => MediaRecommendation.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(growable: false);
  }
}
