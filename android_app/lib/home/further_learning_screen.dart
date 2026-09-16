import 'package:flutter/material.dart';

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
  const FurtherLearningScreen({required this.language, super.key});

  final String language;

  @override
  State<FurtherLearningScreen> createState() => _FurtherLearningScreenState();
}

class _FurtherLearningScreenState extends State<FurtherLearningScreen> {
  LearningMedia _media = LearningMedia.youtube;
  String _genre = _genres[LearningMedia.youtube]!.first;
  String _level = 'A1';
  String _duration = '5–15 minutes';

  void _selectMedia(LearningMedia media) {
    setState(() {
      _media = media;
      _genre = _genres[media]!.first;
    });
  }

  void _showSummary() {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Learning media preferences'),
        content: Text(
          'Find ${_level.toUpperCase()} ${widget.language} ${_media.label.toLowerCase()} '
          'content in the $_genre genre${_media == LearningMedia.song ? '.' : ' lasting $_duration.'}\n\n'
          'Provider-backed recommendations will be connected through the protected '
          'recommendation service. Until then, use these preferences when searching your '
          'preferred media platform.',
        ),
        actions: [
          FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Done')),
        ],
      ),
    );
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
                      onPressed: () => _selectMedia(media),
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
              decoration: const InputDecoration(
                labelText: 'Genre',
                border: OutlineInputBorder(),
              ),
              items: _genres[_media]!
                  .map((genre) => DropdownMenuItem(value: genre, child: Text(genre)))
                  .toList(growable: false),
              onChanged: (genre) => setState(() => _genre = genre!),
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
              onChanged: (level) => setState(() => _level = level!),
            ),
            if (_media != LearningMedia.song) ...[
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _duration,
                decoration: const InputDecoration(
                  labelText: 'Media duration',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  'Under 5 minutes',
                  '5–15 minutes',
                  '15–30 minutes',
                  '30–60 minutes',
                  '60+ minutes',
                ]
                    .map((duration) => DropdownMenuItem(value: duration, child: Text(duration)))
                    .toList(growable: false),
                onChanged: (duration) => setState(() => _duration = duration!),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton.icon(
              key: const Key('find-suitable-media'),
              onPressed: _showSummary,
              icon: const Icon(Icons.search),
              label: const Text('Find suitable media'),
            ),
          ],
        ),
      );
}
