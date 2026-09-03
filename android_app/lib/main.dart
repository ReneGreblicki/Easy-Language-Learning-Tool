import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'auth/auth_service.dart';
import 'config/app_config.dart';
import 'data/deck_repository.dart';
import 'data/local_deck_store.dart';
import 'data/supabase_deck_source.dart';
import 'data/sync_deck_repository.dart';
import 'models/deck.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  const config = AppConfig.fromEnvironment;
  if (!config.isConfigured) {
    runApp(const EasyLanguageFlashcards());
    return;
  }
  await Supabase.initialize(
    url: config.supabaseUrl,
    anonKey: config.publishableKey,
  );
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

class EasyLanguageFlashcards extends StatelessWidget {
  const EasyLanguageFlashcards({
    this.repository,
    this.authService,
    super.key,
  });

  final DeckRepository? repository;
  final AuthService? authService;

  @override
  Widget build(BuildContext context) {
    final fallback = MemoryDeckRepository(<Deck>[]);
    return MaterialApp(
      title: 'Easy Language Flashcards',
      theme: ThemeData(colorSchemeSeed: const Color(0xFF2563EB)),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorSchemeSeed: const Color(0xFF60A5FA),
      ),
      home: authService == null
          ? DeckLibrary(repository: repository ?? fallback)
          : AuthGate(repository: repository!, authService: authService!),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({
    required this.repository,
    required this.authService,
    super.key,
  });

  final DeckRepository repository;
  final AuthService authService;

  @override
  Widget build(BuildContext context) => StreamBuilder<AuthState>(
        stream: authService.changes,
        builder: (context, _) => authService.session == null
            ? LoginScreen(authService: authService)
            : DeckLibrary(repository: repository, authService: authService),
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
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.authService.signIn(
        email: _email.text,
        password: _password.text,
      );
    } on AuthException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _busy = false);
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
          ],
        ),
      );
}

class DeckLibrary extends StatefulWidget {
  const DeckLibrary({
    required this.repository,
    this.authService,
    super.key,
  });

  final DeckRepository repository;
  final AuthService? authService;

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

  Future<void> _removeDownload(Deck deck) async {
    await widget.repository.removeDownload(deck.id);
    if (!mounted) return;
    setState(_refresh);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('My decks'),
          actions: [
            if (widget.authService != null)
              IconButton(
                tooltip: 'Sign out',
                onPressed: widget.authService!.signOut,
                icon: const Icon(Icons.logout),
              ),
          ],
        ),
        body: FutureBuilder<List<Deck>>(
          future: _decks,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return Center(
                child: Text('Synchronization failed: ${snapshot.error}'),
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
                    title: Text(deck.title),
                    subtitle: Text(
                      '${deck.sourceLanguage} → ${deck.translationLanguage} · '
                      '${deck.cards.length} cards',
                    ),
                    trailing: deck.isDownloaded
                        ? PopupMenuButton<String>(
                            onSelected: (value) {
                              if (value == 'remove') _removeDownload(deck);
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(
                                value: 'remove',
                                child: Text('Remove download'),
                              ),
                            ],
                          )
                        : IconButton(
                            tooltip: 'Download',
                            onPressed: () async {
                              await widget.repository.download(deck.id);
                              if (mounted) setState(_refresh);
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
