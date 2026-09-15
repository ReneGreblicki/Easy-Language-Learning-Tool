import 'dart:math';

import 'package:flutter/material.dart';

import '../errors/app_error.dart';
import 'generation_settings.dart';
import 'mobile_generation_service.dart';

class GenerateDeckScreen extends StatefulWidget {
  const GenerateDeckScreen({required this.service, super.key});

  final MobileGenerationService service;

  @override
  State<GenerateDeckScreen> createState() => _GenerateDeckScreenState();
}

class _GenerateDeckScreenState extends State<GenerateDeckScreen> {
  final _title = TextEditingController(text: 'New language deck');
  final _baseWords = TextEditingController(text: '100');
  GenerationLanguage _learning = GenerationLanguage.europeanSpanish;
  GenerationLanguage _translation = GenerationLanguage.usEnglish;
  int _extraForms = 0;
  int _questionPercentage = 20;
  int _pronounChange = 0;
  GenerationCefrMode _cefrMode = GenerationCefrMode.single;
  GenerationCefrLevel _singleLevel = GenerationCefrLevel.a1;
  GenerationCefrLevel _gradualStart = GenerationCefrLevel.a1;
  GenerationCefrLevel _gradualEnd = GenerationCefrLevel.b2;
  final Map<GenerationCefrLevel, TextEditingController> _percentages = {};
  bool _busy = false;
  int _completed = 0;
  int _total = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    for (final level in GenerationCefrLevel.values) {
      _percentages[level] = TextEditingController();
    }
    _resetPercentages();
  }

  @override
  void dispose() {
    _title.dispose();
    _baseWords.dispose();
    for (final controller in _percentages.values) {
      controller.dispose();
    }
    super.dispose();
  }

  List<GenerationCefrLevel> get _selectedLevels {
    final levels = GenerationCefrLevel.values;
    final start = levels.indexOf(_gradualStart);
    final end = levels.indexOf(_gradualEnd);
    return start <= end ? levels.sublist(start, end + 1) : const [];
  }

  int get _maximumBaseWords => 5000 ~/ (1 + _extraForms);
  int get _baseWordValue => int.tryParse(_baseWords.text) ?? 0;
  int get _finalRows => _baseWordValue * (1 + _extraForms);

  void _resetPercentages() {
    final levels = _selectedLevels;
    for (final controller in _percentages.values) {
      controller.text = '0';
    }
    if (levels.isEmpty) return;
    final each = 100 ~/ levels.length;
    var remainder = 100 % levels.length;
    for (final level in levels) {
      _percentages[level]!.text = (each + (remainder-- > 0 ? 1 : 0)).toString();
    }
  }

  MobileGenerationSettings _settings() => MobileGenerationSettings(
        title: _title.text,
        learningLanguage: _learning,
        translationLanguage: _translation,
        baseWords: _baseWordValue,
        extraForms: _extraForms,
        questionPercentage: _questionPercentage,
        pronounChange: _pronounChange,
        cefrMode: _cefrMode,
        singleLevel: _singleLevel,
        gradualStart: _gradualStart,
        gradualEnd: _gradualEnd,
        levelPercentages: {
          for (final level in _selectedLevels)
            level: int.tryParse(_percentages[level]!.text) ?? 0,
        },
        seed: Random.secure().nextInt(1 << 31),
      );

  Future<void> _generate() async {
    FocusScope.of(context).unfocus();
    final settings = _settings();
    final validationError = settings.validate();
    if (validationError != null) {
      setState(() => _error = validationError);
      return;
    }
    setState(() {
      _busy = true;
      _completed = 0;
      _total = settings.finalRows;
      _error = null;
    });
    try {
      final deck = await widget.service.generate(
        settings,
        onProgress: (completed, total) {
          if (mounted) setState(() {
            _completed = completed;
            _total = total;
          });
        },
      );
      if (!mounted) return;
      Navigator.pop(context, deck);
    } catch (error) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = describeAppError(
            error,
            fallback: 'The deck could not be generated. Check your connection and try again.',
          );
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final gradual = _cefrMode == GenerationCefrMode.gradual;
    return PopScope(
      canPop: !_busy,
      child: Scaffold(
        appBar: AppBar(title: const Text('Generate a new deck')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          children: [
            Text(
              'Create a synchronized deck directly on this phone. '
              'The generation service is configured automatically.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            TextField(
              controller: _title,
              enabled: !_busy,
              maxLength: 200,
              decoration: const InputDecoration(
                labelText: 'Deck name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<GenerationLanguage>(
              initialValue: _learning,
              decoration: const InputDecoration(
                labelText: 'Learning language',
                border: OutlineInputBorder(),
              ),
              items: GenerationLanguage.values
                  .map((language) => DropdownMenuItem(
                        value: language,
                        child: Text(language.label),
                      ))
                  .toList(growable: false),
              onChanged: _busy ? null : (value) => setState(() => _learning = value!),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<GenerationLanguage>(
              initialValue: _translation,
              decoration: const InputDecoration(
                labelText: 'Translation language',
                border: OutlineInputBorder(),
              ),
              items: GenerationLanguage.values
                  .map((language) => DropdownMenuItem(
                        value: language,
                        child: Text(language.label),
                      ))
                  .toList(growable: false),
              onChanged: _busy ? null : (value) => setState(() => _translation = value!),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _baseWords,
              enabled: !_busy,
              keyboardType: TextInputType.number,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'Base words',
                helperText: 'Maximum $_maximumBaseWords with $_extraForms extra forms',
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<int>(
              initialValue: _extraForms,
              decoration: const InputDecoration(
                labelText: 'Extra word forms',
                border: OutlineInputBorder(),
              ),
              items: List.generate(
                5,
                (value) => DropdownMenuItem(value: value, child: Text('$value')),
              ),
              onChanged: _busy
                  ? null
                  : (value) => setState(() {
                        _extraForms = value!;
                        if (_baseWordValue > _maximumBaseWords) {
                          _baseWords.text = _maximumBaseWords.toString();
                        }
                      }),
            ),
            const SizedBox(height: 14),
            DropdownButtonFormField<GenerationCefrMode>(
              initialValue: _cefrMode,
              decoration: const InputDecoration(
                labelText: 'CEFR mode',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(
                  value: GenerationCefrMode.single,
                  child: Text('Single level'),
                ),
                DropdownMenuItem(
                  value: GenerationCefrMode.gradual,
                  child: Text('Gradual increase'),
                ),
              ],
              onChanged: _busy ? null : (value) => setState(() => _cefrMode = value!),
            ),
            const SizedBox(height: 14),
            if (!gradual)
              DropdownButtonFormField<GenerationCefrLevel>(
                initialValue: _singleLevel,
                decoration: const InputDecoration(
                  labelText: 'CEFR level',
                  border: OutlineInputBorder(),
                ),
                items: GenerationCefrLevel.values
                    .map((level) => DropdownMenuItem(
                          value: level,
                          child: Text(level.label),
                        ))
                    .toList(growable: false),
                onChanged: _busy ? null : (value) => setState(() => _singleLevel = value!),
              )
            else ...[
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<GenerationCefrLevel>(
                      initialValue: _gradualStart,
                      decoration: const InputDecoration(
                        labelText: 'Start level',
                        border: OutlineInputBorder(),
                      ),
                      items: GenerationCefrLevel.values
                          .map((level) => DropdownMenuItem(
                                value: level,
                                child: Text(level.label),
                              ))
                          .toList(growable: false),
                      onChanged: _busy
                          ? null
                          : (value) => setState(() {
                                _gradualStart = value!;
                                _resetPercentages();
                              }),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<GenerationCefrLevel>(
                      initialValue: _gradualEnd,
                      decoration: const InputDecoration(
                        labelText: 'End level',
                        border: OutlineInputBorder(),
                      ),
                      items: GenerationCefrLevel.values
                          .map((level) => DropdownMenuItem(
                                value: level,
                                child: Text(level.label),
                              ))
                          .toList(growable: false),
                      onChanged: _busy
                          ? null
                          : (value) => setState(() {
                                _gradualEnd = value!;
                                _resetPercentages();
                              }),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (_selectedLevels.isNotEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      children: [
                        for (final level in _selectedLevels)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: TextField(
                              controller: _percentages[level],
                              enabled: !_busy,
                              keyboardType: TextInputType.number,
                              decoration: InputDecoration(
                                labelText: '${level.label} percentage',
                                suffixText: '%',
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 18),
            Text('Questions: $_questionPercentage%'),
            Slider(
              value: _questionPercentage.toDouble(),
              min: 0,
              max: 100,
              divisions: 20,
              onChanged: _busy
                  ? null
                  : (value) => setState(() => _questionPercentage = value.round()),
            ),
            Text('Pronoun-change scale: $_pronounChange'),
            Slider(
              value: _pronounChange.toDouble(),
              min: 0,
              max: 5,
              divisions: 5,
              onChanged: _busy
                  ? null
                  : (value) => setState(() => _pronounChange = value.round()),
            ),
            Card(
              child: ListTile(
                title: const Text('Calculated output'),
                subtitle: Text(
                  '${_finalRows.clamp(0, 5000)} final rows '
                  '($_baseWordValue base words × ${1 + _extraForms})',
                ),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (_busy) ...[
              const SizedBox(height: 18),
              LinearProgressIndicator(
                value: _total == 0 ? null : _completed / _total,
              ),
              const SizedBox(height: 8),
              Text(
                'Generated $_completed of $_total rows. Keep the app open.',
                textAlign: TextAlign.center,
              ),
            ],
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _busy ? null : _generate,
              icon: const Icon(Icons.auto_awesome),
              label: Text(_busy ? 'Generating…' : 'Generate deck'),
            ),
          ],
        ),
      ),
    );
  }
}
