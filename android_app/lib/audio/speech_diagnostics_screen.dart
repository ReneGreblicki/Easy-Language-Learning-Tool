import 'dart:async';
import 'package:flutter/material.dart';
import 'device_speech.dart';
import 'voice_setup.dart';

String speechEngineLabel(String value) => switch (value) {
  'com.google.android.tts' => 'Google speech services',
  'com.samsung.SMT' => 'Samsung text-to-speech',
  _ => value,
};

class SpeechDiagnosticsScreen extends StatefulWidget {
  const SpeechDiagnosticsScreen({required this.speech, required this.language,
    required this.sampleText, super.key});
  final DeviceSpeech speech;
  final String language;
  final String sampleText;
  @override
  State<SpeechDiagnosticsScreen> createState() => _SpeechDiagnosticsScreenState();
}

class _SpeechDiagnosticsScreenState extends State<SpeechDiagnosticsScreen> {
  String? _engine;
  List<String> _engines = [];
  bool _busy = false;
  String? _status;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final info = await widget.speech.diagnostics();
      if (mounted) {
        setState(() {
        _engine = info['engine'] as String?;
        _engines = (info['engines'] as List).cast<String>();
        });
      }
    } catch (error) {
      if (mounted) setState(() => _status = speechErrorText(error));
    }
  }

  Future<void> _changeEngine(String engine) async {
    setState(() { _busy = true; _status = 'Starting ${speechEngineLabel(engine)}…'; });
    try {
      await widget.speech.selectEngine(engine);
      await _load();
      if (mounted) setState(() => _status = 'Engine selected. Test its voice below.');
    } catch (error) {
      if (mounted) setState(() => _status = speechErrorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _test(String text, String language) async {
    setState(() { _busy = true; _status = 'Testing voice…'; });
    try {
      await widget.speech.speak(text, language, awaitCompletion: true)
          .timeout(const Duration(seconds: 15));
      if (mounted) setState(() => _status = 'The speech engine completed the test. Did you hear it?');
    } catch (error) {
      if (mounted) setState(() => _status = speechErrorText(error));
    } finally {
      try { await widget.speech.stop().timeout(const Duration(seconds: 2)); } catch (_) {}
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Test voice')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Text('Speech engine: ${_engine == null ? 'Loading…' : speechEngineLabel(_engine!)}'),
      const SizedBox(height: 16),
      if (_engines.isNotEmpty) DropdownButtonFormField<String>(
        initialValue: _engines.contains(_engine) ? _engine : null,
        decoration: const InputDecoration(labelText: 'Speech engine'),
        items: [for (final engine in _engines) DropdownMenuItem(
          value: engine, child: Text(speechEngineLabel(engine)))],
        onChanged: _busy ? null : (engine) { if (engine != null) _changeEngine(engine); },
      ),
      const SizedBox(height: 16),
      const Text('If the current engine cannot speak, try another installed engine. '
        'Your choice is saved for card and audio playback. Voice audio uses media volume.'),
      const SizedBox(height: 16),
      if (widget.speech.supportsVoiceInstallation) OutlinedButton.icon(
        onPressed: _busy ? null : () => showVoiceSetup(context,
          widget.speech, [widget.language]),
        icon: const Icon(Icons.download),
        label: const Text('Download or manage voices')),
      FilledButton(onPressed: _busy ? null : () => _test('This is a voice playback test.', 'US English'),
        child: const Text('Test English')),
      FilledButton(onPressed: _busy ? null : () => _test(widget.sampleText, widget.language),
        child: const Text('Test card language')),
      if (_status != null) Padding(padding: const EdgeInsets.only(top: 20),
        child: SelectableText(_status!, key: const Key('voice-test-status'))),
    ]),
  );
}
