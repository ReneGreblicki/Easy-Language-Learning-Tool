import 'dart:async';

import 'package:flutter_tts/flutter_tts.dart';

class SpeechVoiceUnavailableException implements Exception {
  const SpeechVoiceUnavailableException(this.language);

  final String language;

  @override
  String toString() =>
      'No $language text-to-speech voice is installed. Open Android Settings, '
      'search for "Text-to-speech", and install or enable a $language voice.';
}

String preferredSpeechLocale(String language) {
  final normalized = language.toLowerCase();
  if (normalized.contains('spanish')) return 'es-ES';
  if (normalized.contains('german')) return 'de-DE';
  if (normalized.contains('portuguese')) return 'pt-PT';
  if (normalized.contains('french')) return 'fr-FR';
  if (normalized.contains('italian')) return 'it-IT';
  if (normalized.contains('thai')) return 'th-TH';
  return 'en-US';
}

String? chooseBestSpeechLocale(String language, Iterable<Object?> installedLocales) {
  final preferred = preferredSpeechLocale(language);
  final available = installedLocales
      .whereType<String>()
      .map((locale) => locale.replaceAll('_', '-'))
      .where((locale) => locale.isNotEmpty)
      .toList(growable: false);
  for (final locale in available) {
    if (locale.toLowerCase() == preferred.toLowerCase()) return locale;
  }
  final languageCode = preferred.split('-').first.toLowerCase();
  for (final locale in available) {
    if (locale.toLowerCase().split('-').first == languageCode) return locale;
  }
  return null;
}

class DeviceSpeech {
  DeviceSpeech({FlutterTts? engine}) : _engine = engine ?? FlutterTts();

  final FlutterTts _engine;

  Future<String> _resolveLocale(String language) async {
    List<Object?> installed = const [];
    try {
      final result = await _engine.getLanguages.timeout(const Duration(seconds: 4));
      if (result is List) installed = result.cast<Object?>();
    } catch (_) {
      // Some Android engines do not enumerate voices. Trying the preferred
      // locale still lets those engines select their own regional fallback.
      return preferredSpeechLocale(language);
    }
    if (installed.isEmpty) return preferredSpeechLocale(language);
    final locale = chooseBestSpeechLocale(language, installed);
    if (locale == null) throw SpeechVoiceUnavailableException(language);
    return locale;
  }

  Future<void> speak(
    String text,
    String language, {
    bool awaitCompletion = false,
  }) async {
    final content = text.trim();
    if (content.isEmpty) return;
    await _engine.stop().timeout(const Duration(seconds: 3));
    final locale = await _resolveLocale(language);
    final languageResult =
        await _engine.setLanguage(locale).timeout(const Duration(seconds: 4));
    if (languageResult == false || languageResult == 0) {
      throw SpeechVoiceUnavailableException(language);
    }
    await _engine.setVolume(1).timeout(const Duration(seconds: 3));
    await _engine.setSpeechRate(0.42).timeout(const Duration(seconds: 3));
    await _engine
        .awaitSpeakCompletion(awaitCompletion)
        .timeout(const Duration(seconds: 3));
    await _engine.speak(content).timeout(
          awaitCompletion
              ? Duration(seconds: (content.length ~/ 8).clamp(15, 120).toInt())
              : const Duration(seconds: 4),
        );
  }

  Future<void> stop() async {
    await _engine.stop();
  }
}
