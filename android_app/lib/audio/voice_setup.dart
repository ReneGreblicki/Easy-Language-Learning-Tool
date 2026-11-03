import 'dart:async';
import 'package:flutter/material.dart';
import '../generation/generation_settings.dart';
import 'device_speech.dart';

Future<void> showVoiceSetup(BuildContext context, DeviceSpeech speech,
    List<String> languages) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  builder: (_) => VoiceSetupPanel(speech: speech, languages: languages),
);

/// Check shared engine assets on every deck open; never persist an assumed
/// installation flag because users can remove voice data outside the app.
class DeckVoiceSetup extends StatefulWidget {
  const DeckVoiceSetup({required this.languages, required this.builder,
    this.speech, super.key});
  final List<String> languages;
  final Widget Function(DeviceSpeech speech) builder;
  final DeviceSpeech? speech;
  @override
  State<DeckVoiceSetup> createState() => _DeckVoiceSetupState();
}

class _DeckVoiceSetupState extends State<DeckVoiceSetup> {
  late final DeviceSpeech _speech = widget.speech ?? DeviceSpeech();
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _check());
  }

  Future<void> _check() async {
    if (!_speech.supportsVoiceInstallation) return;
    try {
      final missing = await _speech.missingOfflineLanguages(widget.languages);
      if (mounted && missing.isNotEmpty) {
        await showVoiceSetup(context, _speech, widget.languages);
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(speechErrorText(error))));
      }
    }
  }

  @override
  void dispose() {
    unawaited(_speech.stop().catchError((_) {}));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(_speech);
}

class VoiceSetupPanel extends StatefulWidget {
  const VoiceSetupPanel({required this.speech, required this.languages, super.key});
  final DeviceSpeech speech;
  final List<String> languages;
  @override
  State<VoiceSetupPanel> createState() => _VoiceSetupPanelState();
}

class _VoiceSetupPanelState extends State<VoiceSetupPanel>
    with WidgetsBindingObserver {
  List<String>? _missing;
  String? _error;
  bool _busy = false;
  bool _installerOpened = false;
  bool _resumePending = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_check());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _installerOpened) {
      _installerOpened = false;
      if (_busy) {
        _resumePending = true;
      } else {
        unawaited(_check(refresh: true));
      }
    }
  }

  Future<void> _check({bool refresh = false}) async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      if (refresh) await widget.speech.refreshVoiceData();
      final missing = await widget.speech.missingOfflineLanguages(widget.languages);
      if (mounted) setState(() => _missing = missing);
    } catch (error) {
      if (mounted) setState(() => _error = speechErrorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _download() async {
    setState(() { _busy = true; _error = null; });
    _installerOpened = true;
    try {
      await widget.speech.installVoiceData();
    } catch (error) {
      _installerOpened = false;
      if (mounted) setState(() => _error = speechErrorText(error));
    } finally {
      if (mounted) {
        setState(() => _busy = false);
        if (_resumePending) {
          _resumePending = false;
          unawaited(_check(refresh: true));
        }
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SafeArea(child: Padding(
    padding: const EdgeInsets.all(20),
    child: SingleChildScrollView(child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Offline voices', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        const Text('Download each language once in the speech engine’s screen. '
          'The voices stay on your phone and are reused by other decks. '
          'Only the download needs an internet connection.'),
        const SizedBox(height: 12),
        if (_busy) const LinearProgressIndicator(),
        if (_missing != null && _error == null) ...[
          if (_missing!.isEmpty) const Text('This deck’s voices are ready for offline use.'),
          if (_missing!.isNotEmpty) Text('Download needed: '
            '${_missing!.map(displayLanguageName).join(', ')}. '
            'Choose these languages in the download screen.'),
        ],
        if (_error != null) Text(_error!),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: _busy ? null : _download,
          icon: const Icon(Icons.download),
          label: Text(_missing?.isNotEmpty == true ? 'Download voices' : 'Manage voices')),
        OutlinedButton(onPressed: _busy ? null : () => _check(refresh: true),
          child: const Text('Check again')),
        TextButton(onPressed: () => Navigator.pop(context),
          child: const Text('Continue to deck')),
      ],
    )),
  ));
}
