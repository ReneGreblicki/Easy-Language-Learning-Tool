import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'auth/auth_service.dart';
import 'audio/device_speech.dart';
import 'config/app_config.dart';
import 'data/deck_repository.dart';
import 'data/local_deck_store.dart';
import 'data/supabase_deck_source.dart';
import 'data/sync_deck_repository.dart';
import 'errors/app_error.dart';
import 'models/deck.dart';
import 'study/audio_screen.dart';
import 'study/list_screen.dart';
import 'study/study_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  const config = AppConfig.fromEnvironment;
  if (!config.isConfigured) {
    runApp(const EasyLanguageFlashcards());
    return;
  }
  try {
    await Supabase.initialize(
      url: config.supabaseUrl,
      publishableKey: config.publishableKey,
    );
  } catch (error) {
    runApp(
      _StartupFailureApp(
        message: describeAppError(
          error,
          fallback: 'The app could not start its account service. Close it and try again.',
        ),
      ),
    );
    return;
  }
  final client = Supabase.instance.client;
  runApp(
    EasyLanguageFlashcards(
      repository: SyncDeckRepository(
        local: LocalDeckStore(),
        cloud: SupabaseDeckSource(client),
      ),
      authService: AuthService(client),
    ),
  );
}

class _StartupFailureApp extends StatelessWidget {
  const _StartupFailureApp({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Easy Language Flashcards',
        darkTheme: ThemeData.dark(),
        themeMode: ThemeMode.dark,
        home: Scaffold(
          appBar: AppBar(title: const Text('Cannot start app')),
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(message, textAlign: TextAlign.center),
            ),
          ),
        ),
      );
}

class EasyLanguageFlashcards extends StatefulWidget {
  const EasyLanguageFlashcards({
    this.repository,
    this.authService,
    super.key,
  });

  final DeckRepository? repository;
  final AuthService? authService;

  @override
  State<EasyLanguageFlashcards> createState() => _EasyLanguageFlashcardsState();
}

class _EasyLanguageFlashcardsState extends State<EasyLanguageFlashcards> {
  ThemeMode _themeMode = ThemeMode.dark;

  void _toggleTheme() => setState(() {
        _themeMode = _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
      });

  @override
  Widget build(BuildContext context) {
    final fallback = MemoryDeckRepository(<Deck>[]);
    return MaterialApp(
      title: 'Easy Language Flashcards',
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF7F9FC),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E74B5)),
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF111827),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF60A5FA),
          brightness: Brightness.dark,
          surface: const Color(0xFF172033),
        ),
      ),
      themeMode: _themeMode,
      home: widget.authService == null
          ? DeckLibrary(repository: widget.repository ?? fallback, onToggleTheme: _toggleTheme)
          : AuthGate(
              repository: widget.repository!,
              authService: widget.authService!,
              onToggleTheme: _toggleTheme,
            ),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({
    required this.repository,
    required this.authService,
    required this.onToggleTheme,
    super.key,
  });

  final DeckRepository repository;
  final AuthService authService;
  final VoidCallback onToggleTheme;

  @override
  Widget build(BuildContext context) => StreamBuilder<AuthState>(
        stream: authService.changes,
        builder: (context, _) => authService.session == null
            ? LoginScreen(authService: authService)
            : DeckLibrary(
                repository: repository,
                authService: authService,
                onToggleTheme: onToggleTheme,
              ),
      );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({required this.authService, super.key});

  final AuthService authService;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    final email = _email.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    if (_password.text.isEmpty) {
      setState(() => _error = 'Enter your password.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.authService.signIn(
        email: _email.text,
        password: _password.text,
      );
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = describeAppError(
            error,
            fallback: 'Sign-in failed. Check your account details and try again.',
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _register() async {
    final username = TextEditingController();
    final email = TextEditingController(text: _email.text);
    final password = TextEditingController();
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Create account'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: username,
                decoration: const InputDecoration(labelText: 'Username'),
              ),
              TextField(
                controller: email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: password,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (accepted != true) {
      username.dispose();
      email.dispose();
      password.dispose();
      return;
    }
    final registrationError = username.text.trim().length < 3
        ? 'Username must contain at least 3 characters.'
        : !email.text.trim().contains('@')
            ? 'Enter a valid email address.'
            : password.text.length < 8
                ? 'Password must contain at least 8 characters.'
                : null;
    if (registrationError != null) {
      if (mounted) setState(() => _error = registrationError);
      username.dispose();
      email.dispose();
      password.dispose();
      return;
    }
    try {
      await widget.authService.register(
        username: username.text,
        email: email.text,
        password: password.text,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Account created. Open the confirmation email once; the link will return to this app.',
            ),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = describeAppError(
            error,
            fallback: 'The account could not be created. Check the details and try again.',
          ),
        );
      }
    } finally {
      username.dispose();
      email.dispose();
      password.dispose();
    }
  }

  Future<void> _resetPassword() async {
    if (!_email.text.trim().contains('@')) {
      setState(() => _error = 'Enter a valid email address first.');
      return;
    }
    try {
      await widget.authService.resetPassword(_email.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Password-reset email sent.')),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = describeAppError(
            error,
            fallback: 'The password-reset email could not be sent. Try again later.',
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Sign in')),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: true,
              autofillHints: const [AutofillHints.password],
              decoration: const InputDecoration(labelText: 'Password'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _signIn,
              child: Text(_busy ? 'Signing in…' : 'Sign in'),
            ),
            TextButton(
              onPressed: _busy ? null : _register,
              child: const Text('Create account'),
            ),
            TextButton(
              onPressed: _busy ? null : _resetPassword,
              child: const Text('Forgot password?'),
            ),
          ],
        ),
      );
}

class DeckLibrary extends StatefulWidget {
  const DeckLibrary({
    required this.repository,
    required this.onToggleTheme,
    this.authService,
    super.key,
  });

  final DeckRepository repository;
  final AuthService? authService;
  final VoidCallback onToggleTheme;

  @override
  State<DeckLibrary> createState() => _DeckLibraryState();
}

class _DeckLibraryState extends State<DeckLibrary> {
  late Future<List<Deck>> _decks;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    _decks = widget.repository.cloudLibrary();
  }

  void _showError(Object error, String fallback) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(describeAppError(error, fallback: fallback))),
    );
  }

  Future<void> _removeDownload(Deck deck) async {
    try {
      await widget.repository.removeDownload(deck.id);
      if (mounted) setState(_refresh);
    } catch (error) {
      _showError(error, 'The phone download could not be removed. Try again.');
    }
  }

  Future<void> _confirmRemoveDownload(Deck deck) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove download?'),
        content: const Text(
          'This removes only the files stored on this phone. '
          'The desktop and cloud copies remain unchanged.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Remove download'),
          ),
        ],
      ),
    );
    if (confirmed == true) await _removeDownload(deck);
  }

  Future<void> _confirmDeleteEverywhere(Deck deck) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete everywhere?'),
        content: const Text(
          'This removes the synchronized cloud copy and this phone’s download. '
          'The original workbook and all desktop files remain unchanged. '
          'The cloud copy can be restored for 30 days.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete everywhere'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.repository.deleteEverywhere(deck.id);
      if (mounted) setState(_refresh);
    } catch (error) {
      _showError(error, 'The cloud copy could not be deleted. Refresh and try again.');
    }
  }

  Future<void> _openDeck(Deck deck) async {
    if (deck.cards.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This deck has no cards.')),
      );
      return;
    }
    final activity = await showDialog<_DeckActivity>(
      context: context,
      builder: (context) => const _ActivityDialog(),
    );
    if (activity == null || !mounted) return;
    final configuration = await showDialog<_StudyConfiguration>(
      context: context,
      builder: (context) => _StudySetupDialog(deck: deck, activity: activity),
    );
    if (configuration == null || !mounted) return;
    final includeAudio = activity != _DeckActivity.list;
    Deck sourceDeck;
    try {
      sourceDeck = deck.isDownloaded && !includeAudio && !configuration.downloadAudio
          ? deck
          : await widget.repository.loadDeck(
              deck.id,
              includeAudio: includeAudio || configuration.downloadAudio,
              downloadAudio: configuration.downloadAudio,
              fromRank: configuration.fromRank,
              toRank: configuration.toRank,
            );
    } catch (error) {
      _showError(error, 'The deck could not be opened. Refresh and try again.');
      return;
    }
    if (!mounted) return;
    final selectedDeck = sourceDeck.copyWithCards(
      sourceDeck.cards
          .where((card) =>
              card.rank >= configuration.fromRank && card.rank <= configuration.toRank)
          .toList(growable: false),
    );
    final Widget screen = switch (activity) {
      _DeckActivity.flashcards => StudyScreen(
          deck: selectedDeck,
          repository: widget.repository,
          mode: configuration.mode,
          voiceGender: configuration.voiceGender,
          onToggleTheme: widget.onToggleTheme,
        ),
      _DeckActivity.audio => AudioStudyScreen(
          deck: selectedDeck,
          repository: widget.repository,
          mode: configuration.mode,
          voiceGender: configuration.voiceGender,
          onToggleTheme: widget.onToggleTheme,
        ),
      _DeckActivity.list => StudyListScreen(
          deck: selectedDeck,
          mode: configuration.mode,
          onToggleTheme: widget.onToggleTheme,
        ),
    };
    await Navigator.push<void>(context, MaterialPageRoute(builder: (_) => screen));
  }

  Future<void> _showTrash() async {
    List<Deck> trashed;
    try {
      trashed = await widget.repository.trashedDecks();
    } catch (error) {
      _showError(error, 'Cloud Trash could not be loaded. Try again.');
      return;
    }
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Cloud Trash'),
        content: SizedBox(
          width: double.maxFinite,
          child: trashed.isEmpty
              ? const Text('Trash is empty.')
              : ListView.builder(
                  shrinkWrap: true,
                  itemCount: trashed.length,
                  itemBuilder: (_, index) {
                    final deck = trashed[index];
                    return ListTile(
                      title: Text(deck.title),
                      subtitle: const Text('Recoverable for 30 days'),
                      trailing: TextButton(
                        onPressed: () async {
                          try {
                            await widget.repository.restore(deck.id);
                            if (dialogContext.mounted) Navigator.pop(dialogContext);
                            if (mounted) setState(_refresh);
                          } catch (error) {
                            if (dialogContext.mounted) Navigator.pop(dialogContext);
                            _showError(
                              error,
                              'The deck could not be restored. Refresh and try again.',
                            );
                          }
                        },
                        child: const Text('Restore'),
                      ),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Future<void> _signOut() async {
    try {
      await widget.authService?.signOut();
    } catch (error) {
      _showError(error, 'Sign-out failed. Check your connection and try again.');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('My decks'),
          actions: [
            IconButton(
              tooltip: 'Switch light/dark theme',
              onPressed: widget.onToggleTheme,
              icon: const Icon(Icons.brightness_6_outlined),
            ),
            IconButton(
              tooltip: 'Cloud Trash',
              onPressed: _showTrash,
              icon: const Icon(Icons.restore_from_trash_outlined),
            ),
            if (widget.authService != null)
              IconButton(
                tooltip: 'Sign out',
                onPressed: _signOut,
                icon: const Icon(Icons.logout),
              ),
          ],
        ),
        body: FutureBuilder<List<Deck>>(
          future: _decks,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        describeAppError(
                          snapshot.error!,
                          fallback: 'Deck synchronization failed. Try again.',
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: () => setState(_refresh),
                        icon: const Icon(Icons.refresh),
                        label: const Text('Try again'),
                      ),
                    ],
                  ),
                ),
              );
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final decks = snapshot.data!;
            if (decks.isEmpty) {
              return const Center(
                child: Text('Generate a deck on desktop, then synchronize it here.'),
              );
            }
            return RefreshIndicator(
              onRefresh: () async => setState(_refresh),
              child: ListView.builder(
                itemCount: decks.length,
                itemBuilder: (context, index) {
                  final deck = decks[index];
                  return ListTile(
                    onTap: () => _openDeck(deck),
                    title: Text(deck.title),
                    subtitle: Text(
                      '${deck.sourceLanguage} → ${deck.translationLanguage} · '
                      '${deck.cards.length} cards',
                    ),
                    trailing: deck.isDownloaded
                        ? PopupMenuButton<String>(
                            onSelected: (value) {
                              if (value == 'remove') {
                                _confirmRemoveDownload(deck);
                              } else if (value == 'delete_everywhere') {
                                _confirmDeleteEverywhere(deck);
                              }
                            },
                            itemBuilder: (_) => const [
                                  PopupMenuItem(
                                    value: 'remove',
                                    child: Text('Remove download'),
                                  ),
                                  PopupMenuItem(
                                    value: 'delete_everywhere',
                                    child: Text('Delete everywhere'),
                                  ),
                                ],
                          )
                        : IconButton(
                            tooltip: 'Download',
                            onPressed: () async {
                              try {
                                await widget.repository.download(deck.id);
                                if (mounted) setState(_refresh);
                              } catch (error) {
                                _showError(
                                  error,
                                  'The deck could not be downloaded. Try again.',
                                );
                              }
                            },
                            icon: const Icon(Icons.cloud_download_outlined),
                          ),
                  );
                },
              ),
            );
          },
        ),
      );
}

enum _DeckActivity { flashcards, audio, list }

class _ActivityDialog extends StatelessWidget {
  const _ActivityDialog();

  @override
  Widget build(BuildContext context) => SimpleDialog(
        title: const Text('Choose activity'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, _DeckActivity.flashcards),
            child: const ListTile(
              leading: Icon(Icons.style_outlined),
              title: Text('Flashcards'),
            ),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, _DeckActivity.audio),
            child: const ListTile(
              leading: Icon(Icons.headphones_outlined),
              title: Text('Listen to audio'),
            ),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(context, _DeckActivity.list),
            child: const ListTile(
              leading: Icon(Icons.list_alt_outlined),
              title: Text('View list'),
            ),
          ),
        ],
      );
}

class _StudyConfiguration {
  const _StudyConfiguration(
    this.mode,
    this.fromRank,
    this.toRank,
    this.downloadAudio,
    this.voiceGender,
  );

  final StudyContentMode mode;
  final int fromRank;
  final int toRank;
  final bool downloadAudio;
  final SpeechVoiceGender voiceGender;
}

class _StudySetupDialog extends StatefulWidget {
  const _StudySetupDialog({required this.deck, required this.activity});

  final Deck deck;
  final _DeckActivity activity;

  @override
  State<_StudySetupDialog> createState() => _StudySetupDialogState();
}

class _StudySetupDialogState extends State<_StudySetupDialog> {
  StudyContentMode _mode = StudyContentMode.both;
  bool _selectedRows = false;
  bool _downloadAudio = false;
  SpeechVoiceGender _voiceGender = SpeechVoiceGender.female;
  late final TextEditingController _from;
  late final TextEditingController _to;
  late final int _minimum;
  late final int _maximum;
  String? _error;

  @override
  void initState() {
    super.initState();
    final ranks = widget.deck.cards.map((card) => card.rank);
    _minimum = ranks.reduce((a, b) => a < b ? a : b);
    _maximum = ranks.reduce((a, b) => a > b ? a : b);
    _from = TextEditingController(text: _minimum.toString());
    _to = TextEditingController(text: _maximum.toString());
  }

  @override
  void dispose() {
    _from.dispose();
    _to.dispose();
    super.dispose();
  }

  void _start() {
    final from = _selectedRows ? int.tryParse(_from.text) : _minimum;
    final to = _selectedRows ? int.tryParse(_to.text) : _maximum;
    if (from == null || to == null || from < _minimum || to > _maximum || from > to) {
      setState(() => _error = 'Choose an inclusive range from $_minimum to $_maximum.');
      return;
    }
    Navigator.pop(
      context,
      _StudyConfiguration(_mode, from, to, _downloadAudio, _voiceGender),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(switch (widget.activity) {
          _DeckActivity.flashcards => 'Flashcard settings',
          _DeckActivity.audio => 'Audio settings',
          _DeckActivity.list => 'List settings',
        }),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<StudyContentMode>(
                initialValue: _mode,
                decoration: const InputDecoration(labelText: 'Cards'),
                items: StudyContentMode.values
                    .map((mode) => DropdownMenuItem(value: mode, child: Text(mode.label)))
                    .toList(growable: false),
                onChanged: (mode) => setState(() => _mode = mode!),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Selected rows only'),
                value: _selectedRows,
                onChanged: (value) => setState(() => _selectedRows = value),
              ),
              if (widget.activity != _DeckActivity.list)
                DropdownButtonFormField<SpeechVoiceGender>(
                  initialValue: _voiceGender,
                  decoration: const InputDecoration(labelText: 'Phone voice'),
                  items: SpeechVoiceGender.values
                      .map(
                        (gender) => DropdownMenuItem(
                          value: gender,
                          child: Text(gender.label),
                        ),
                      )
                      .toList(growable: false),
                  onChanged: (gender) => setState(() => _voiceGender = gender!),
                ),
              if (widget.activity != _DeckActivity.list)
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Download desktop TTS audio'),
                  subtitle: const Text(
                    'Optional fallback if the selected phone voice is unavailable.',
                  ),
                  value: _downloadAudio,
                  onChanged: (value) => setState(() => _downloadAudio = value ?? false),
                ),
              if (_selectedRows)
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _from,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'From rank'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _to,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'To rank'),
                      ),
                    ),
                  ],
                ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: _start, child: const Text('Start')),
        ],
      );
}
