import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../errors/app_error.dart';
import 'further_learning_service.dart';

enum LearningMedia {
  youtube('YouTube video', Icons.ondemand_video_outlined),
  podcast('Podcast', Icons.podcasts_outlined),
  series('Series', Icons.tv_outlined),
  movie('Movie', Icons.movie_outlined),
  song('Song', Icons.music_note_outlined);

  const LearningMedia(this.label, this.icon);
  final String label;
  final IconData icon;
}

const _genres = <LearningMedia, List<String>>{
  LearningMedia.youtube: ['Documentary', 'Education', 'Travel', 'News', 'Comedy', 'Lifestyle'],
  LearningMedia.podcast: ['Conversation', 'Education', 'News', 'Culture', 'Stories', 'Technology'],
  LearningMedia.series: ['Comedy', 'Drama', 'Crime', 'Documentary', 'Family', 'Science fiction'],
  LearningMedia.movie: ['Comedy', 'Drama', 'Adventure', 'Documentary', 'Family', 'Thriller'],
  LearningMedia.song: ['Pop', 'Rock', 'Hip-hop', 'Folk', 'Electronic', 'Ballad'],
};

class FurtherLearningScreen extends StatefulWidget {
  const FurtherLearningScreen({required this.language, this.service, super.key});

  final String language;
  final FurtherLearningService? service;

  @override
  State<FurtherLearningScreen> createState() => _FurtherLearningScreenState();
}

class _FurtherLearningScreenState extends State<FurtherLearningScreen> {
  LearningMedia _media = LearningMedia.youtube;
  String _genre = _genres[LearningMedia.youtube]!.first;
  String _level = 'A1';
  String _duration = '5–15 minutes';
  bool _loading = false;
  String? _error;
  List<MediaRecommendation> _results = const [];

  void _selectMedia(LearningMedia media) {
    setState(() {
      _media = media;
      _genre = _genres[media]!.first;
      _results = const [];
      _error = null;
    });
  }

  Future<void> _find() async {
    final service = widget.service;
    if (service == null) {
      setState(() => _error = 'Sign in to receive current media recommendations.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _results = const [];
    });
    try {
      final results = await service.recommend(
        language: widget.language,
        media: _media.name,
        genre: _genre,
        level: _level,
        duration: _media == LearningMedia.movie || _media == LearningMedia.song
            ? null
            : _duration,
      );
      if (mounted) setState(() => _results = results);
    } catch (error) {
      if (mounted) {
        setState(() => _error = describeAppError(
              error,
              fallback: 'Suitable media could not be found right now. Try different settings.',
            ));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _open(MediaRecommendation recommendation) async {
    final uri = Uri.tryParse(recommendation.url);
    if (uri == null || !await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (mounted) setState(() => _error = 'This recommendation link could not be opened.');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Further learning')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          children: [
            Card(
              color: Theme.of(context).colorScheme.secondaryContainer,
              child: ListTile(
                leading: const Icon(Icons.translate),
                title: const Text('Learning language'),
                subtitle: Text(widget.language),
              ),
            ),
            const SizedBox(height: 18),
            Text('Media', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 2.3,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                for (final media in LearningMedia.values)
                  Semantics(
                    selected: media == _media,
                    child: FilledButton.tonalIcon(
                      key: Key('media-${media.name}'),
                      onPressed: _loading ? null : () => _selectMedia(media),
                      icon: Icon(media.icon),
                      label: Text(media.label),
                      style: media == _media
                          ? FilledButton.styleFrom(
                              backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                            )
                          : null,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 18),
            DropdownButtonFormField<String>(
              key: ValueKey('genre-${_media.name}'),
              initialValue: _genre,
              decoration: const InputDecoration(labelText: 'Genre', border: OutlineInputBorder()),
              items: _genres[_media]!
                  .map((genre) => DropdownMenuItem(value: genre, child: Text(genre)))
                  .toList(growable: false),
              onChanged: _loading ? null : (genre) => setState(() => _genre = genre!),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<String>(
              initialValue: _level,
              decoration: const InputDecoration(
                labelText: 'Desired language level',
                border: OutlineInputBorder(),
              ),
              items: const ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
                  .map((level) => DropdownMenuItem(value: level, child: Text(level)))
                  .toList(growable: false),
              onChanged: _loading ? null : (level) => setState(() => _level = level!),
            ),
            if (_media != LearningMedia.song && _media != LearningMedia.movie) ...[
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _duration,
                decoration: InputDecoration(
                  labelText: _media == LearningMedia.series ? 'Episode duration' : 'Media duration',
                  border: const OutlineInputBorder(),
                ),
                items: const [
                  'Under 5 minutes', '5–15 minutes', '15–30 minutes',
                  '30–60 minutes', '60+ minutes',
                ].map((duration) => DropdownMenuItem(value: duration, child: Text(duration)))
                    .toList(growable: false),
                onChanged: _loading ? null : (duration) => setState(() => _duration = duration!),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton.icon(
              key: const Key('find-suitable-media'),
              onPressed: _loading ? null : _find,
              icon: _loading
                  ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.search),
              label: Text(_loading ? 'Finding three options…' : 'Find suitable media'),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            for (final result in _results) ...[
              const SizedBox(height: 14),
              Card(
                clipBehavior: Clip.antiAlias,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (result.imageUrl != null && result.imageUrl!.isNotEmpty)
                      Image.network(
                        result.imageUrl!,
                        height: 150,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                      ),
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(result.title, style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 8),
                          Text(result.description),
                          const SizedBox(height: 10),
                          Align(
                            alignment: Alignment.centerRight,
                            child: FilledButton.tonalIcon(
                              onPressed: () => _open(result),
                              icon: const Icon(Icons.open_in_new),
                              label: const Text('Open'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      );
}
