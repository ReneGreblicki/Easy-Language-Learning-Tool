import 'package:flutter/material.dart';

import '../analytics/learning_analytics.dart';
import '../auth/auth_service.dart';
import '../errors/app_error.dart';
import 'app_preferences.dart';

class AccountSettingsScreen extends StatefulWidget {
  const AccountSettingsScreen({required this.auth, required this.openLogin, super.key});
  final AuthService? auth;
  final void Function(String? email) openLogin;
  @override
  State<AccountSettingsScreen> createState() => _AccountSettingsScreenState();
}

class _AccountSettingsScreenState extends State<AccountSettingsScreen> {
  final _preferences = AppPreferences();
  List<String> _accounts = [];
  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    final accounts = await _preferences.accounts();
    if (mounted) setState(() => _accounts = accounts);
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Account settings')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Text(widget.auth?.session?.user.email ?? 'Not signed in',
          style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 12),
      const Text('Accounts keep separate downloads and study settings. Enter your password when switching accounts. Passwords are not saved in the account list.'),
      const SizedBox(height: 20),
      for (final email in _accounts)
        ListTile(
          title: Text(email),
          subtitle: Text(email == widget.auth?.session?.user.email ? 'Current account' : 'Sign in to switch'),
          onTap: email == widget.auth?.session?.user.email ? null : () => widget.openLogin(email),
          trailing: IconButton(tooltip: 'Forget saved account', icon: const Icon(Icons.close),
            onPressed: () async { await _preferences.forget(email); await _load(); }),
        ),
      FilledButton.icon(onPressed: widget.auth == null ? null : () => widget.openLogin(null),
          icon: const Icon(Icons.person_add_outlined), label: const Text('Add another account')),
      const SizedBox(height: 12),
      const Text('Forgetting an account removes its saved email from this menu. It does not delete its cloud decks or desktop files.'),
    ]),
  );
}

class DisplaySettingsScreen extends StatelessWidget {
  const DisplaySettingsScreen({required this.onToggleTheme, super.key});
  final VoidCallback onToggleTheme;
  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      appBar: AppBar(title: const Text('Display settings')),
      body: ListView(children: [
        SwitchListTile(title: const Text('Dark mode'),
          subtitle: Text(dark ? 'Dark appearance' : 'Light appearance'),
          value: dark, onChanged: (_) => onToggleTheme()),
      ]),
    );
  }
}

class PrivacySettingsScreen extends StatefulWidget {
  const PrivacySettingsScreen({this.analytics, super.key});
  final LearningAnalytics? analytics;
  @override
  State<PrivacySettingsScreen> createState() => _PrivacySettingsScreenState();
}

class _PrivacySettingsScreenState extends State<PrivacySettingsScreen> {
  bool _busy = false;
  String? _error;
  @override
  void initState() { super.initState(); widget.analytics?.addListener(_refresh); }
  void _refresh() { if (mounted) setState(() {}); }
  @override
  void dispose() { widget.analytics?.removeListener(_refresh); super.dispose(); }
  Future<void> _setEnabled(bool enabled) async {
    setState(() { _busy = true; _error = null; });
    try { await widget.analytics?.setEnabled(enabled); }
    catch (error) {
      if (mounted) {
        setState(() => _error = describeAppError(error,
          fallback: 'The privacy preference could not be saved. Try again online.'));
      }
    } finally { if (mounted) setState(() => _busy = false); }
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Privacy settings')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Text('Data collection', style: Theme.of(context).textTheme.headlineSmall),
      SwitchListTile(contentPadding: EdgeInsets.zero,
        title: const Text('Share learning milestones'),
        subtitle: const Text('Optional. Off by default. Your study features work without it.'),
        value: widget.analytics?.enabled ?? false,
        onChanged: _busy || widget.analytics?.ready != true ? null : _setEnabled),
      if (widget.analytics?.pendingDeletion == true)
        const Text('Collection is off on this device. Deletion from the server is pending an internet connection.'),
      if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      const Text('When enabled, we record the first deck you study, the time you reach 10, 100, 500 and 1,000 unique cards revealed in each learning language, and each successfully generated mobile deck. Returning to the front of a card does not count. A card counts once per learning language, including across devices. Repeated practice does not count again.'),
      const SizedBox(height: 12),
      const Text('These records contain your account identifier, language, card identifier for deduplication, event type, milestone and timestamp. They are linked to your account, not anonymous. Card text, deck titles, passwords, contacts, precise location and advertising identifiers are not included in learning analytics.'),
      const SizedBox(height: 12),
      const Text('Event records and retry receipts older than 90 days are deleted by a daily server job. Unique-card identifiers, per-language counts and first-use markers remain while sharing is enabled, so milestones do not repeat. Turning sharing off deletes analytics records and counters when the server receives the request. An offline phone retries when it reconnects. Turning sharing on again starts a new measurement period.'),
      if (widget.analytics != null) TextButton(
        onPressed: _busy ? null : () => _setEnabled(false),
        child: const Text('Turn off and delete learning analytics')),
      const Divider(height: 32),
      Text('Data needed to run the app', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 12),
      const Text('Supabase handles your email/account profile, sign-in session, cloud decks, cards, study progress and optional uploaded audio. Session tokens keep you signed in. Saved account emails and display settings stay on this device. Downloads and local progress are separated by account and remain until removed or app data is cleared.'),
      const SizedBox(height: 12),
      const Text('Mobile deck removal clears the local download and schedules cloud cleanup after 14 days. Using or downloading the deck again cancels that cleanup. Cleanup runs when the app connects; the deadline does not guarantee immediate deletion while all devices are offline. Desktop source files are never removed by phone actions. There is no 90-day inactivity deletion of decks.'),
      const SizedBox(height: 12),
      const Text('Account details, active cloud decks and progress are retained while the account exists, unless removed through the available deck controls. Generation jobs, requested vocabulary/settings, generated results and operational token/latency/error records are retained for service operation; automatic expiry is not currently configured for these operational records. Account deletion is not available in this app version.'),
      const SizedBox(height: 12),
      const Text('Generation and Further Learning requests are sent to OpenAI through the backend. Spoken text may be processed by your selected speech provider. Those providers and hosting logs/backups follow their own retention settings; this app does not control those periods.'),
      const Divider(height: 32),
      Text('Google Play statistics', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 12),
      const Text('Google Play may report aggregate installs/uninstalls, active use, store conversion, device/Android version, country, ratings and crashes for Play-distributed apps. Those statistics follow Google settings and are separate from this optional learning-milestone switch. Installing an APK directly does not create a Google Play store acquisition.'),
    ]),
  );
}
