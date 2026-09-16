import 'package:flutter/material.dart';

class LandingMenu extends StatelessWidget {
  const LandingMenu({
    required this.selectedLanguage,
    required this.selectedDeckTitle,
    required this.onSelectLanguage,
    required this.onSelectDeck,
    required this.onGenerate,
    required this.onFlashcards,
    required this.onAudio,
    required this.onList,
    required this.onFurtherLearning,
    required this.onInstructions,
    super.key,
  });

  final String? selectedLanguage;
  final String? selectedDeckTitle;
  final VoidCallback onSelectLanguage;
  final VoidCallback onSelectDeck;
  final VoidCallback onGenerate;
  final VoidCallback onFlashcards;
  final VoidCallback onAudio;
  final VoidCallback onList;
  final VoidCallback onFurtherLearning;
  final VoidCallback onInstructions;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        key: const Key('landing-menu'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 32),
        child: Column(
          children: [
          Card(
            color: Theme.of(context).colorScheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _ContextLine(
                    icon: Icons.translate,
                    label: 'Learning language',
                    value: selectedLanguage ?? 'Not selected',
                  ),
                  const SizedBox(height: 10),
                  _ContextLine(
                    icon: Icons.style_outlined,
                    label: 'Selected deck',
                    value: selectedDeckTitle ?? 'Not selected',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _LandingAction(
            key: const Key('select-language'),
            icon: Icons.translate,
            title: 'Select a language',
            subtitle: 'Filter your deck library',
            onTap: onSelectLanguage,
          ),
          _LandingAction(
            key: const Key('select-deck'),
            icon: Icons.style_outlined,
            title: 'Select a deck',
            subtitle: selectedDeckTitle ?? 'Choose a deck for every practice mode',
            onTap: onSelectDeck,
          ),
          _LandingAction(
            key: const Key('generate-new-deck'),
            icon: Icons.auto_awesome,
            title: 'Generate a new deck',
            subtitle: 'Create, synchronize, and keep it offline',
            onTap: onGenerate,
            emphasized: true,
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 18, 4, 6),
            child: Text('PRACTICE', style: TextStyle(fontWeight: FontWeight.w500)),
          ),
          _LandingAction(
            key: const Key('practice-flashcards'),
            icon: Icons.view_carousel_outlined,
            title: 'Practice flashcards',
            onTap: onFlashcards,
          ),
          _LandingAction(
            key: const Key('practice-audio'),
            icon: Icons.headphones_outlined,
            title: 'Practice audio',
            onTap: onAudio,
          ),
          _LandingAction(
            key: const Key('practice-list'),
            icon: Icons.list_alt_outlined,
            title: 'Practice list',
            onTap: onList,
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 18, 4, 6),
            child: Text('LEARN MORE', style: TextStyle(fontWeight: FontWeight.w500)),
          ),
          _LandingAction(
            key: const Key('further-learning'),
            icon: Icons.explore_outlined,
            title: 'Further learning',
            subtitle: 'Choose suitable external media',
            onTap: onFurtherLearning,
          ),
          _LandingAction(
            key: const Key('learning-instructions'),
            icon: Icons.route_outlined,
            title: 'Learning instructions',
            subtitle: 'Follow the roadmap to language fluency',
            onTap: onInstructions,
          ),
          ],
        ),
      );
}

class _ContextLine extends StatelessWidget {
  const _ContextLine({required this.icon, required this.label, required this.value});

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.bodySmall),
                Text(value, maxLines: 1, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
        ],
      );
}

class _LandingAction extends StatelessWidget {
  const _LandingAction({
    required this.icon,
    required this.title,
    required this.onTap,
    this.subtitle,
    this.emphasized = false,
    super.key,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Card(
      color: emphasized ? colors.primaryContainer : null,
      child: ListTile(
        minVerticalPadding: 12,
        leading: Icon(icon),
        title: Text(title),
        subtitle: subtitle == null ? null : Text(subtitle!),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
