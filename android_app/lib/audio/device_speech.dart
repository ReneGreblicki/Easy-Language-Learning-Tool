import 'dart:async';
import 'dart:io';

import 'package:flutter_tts/flutter_tts.dart';

enum SpeechVoiceGender { female, male }

extension SpeechVoiceGenderLabel on SpeechVoiceGender {
  String get label => switch (this) {
        SpeechVoiceGender.female => 'Female',
        SpeechVoiceGender.male => 'Male',
      };
}

class SpeechVoiceUnavailableException implements Exception {
  const SpeechVoiceUnavailableException(this.language);

  final String language;

  @override
  String toString() =>
      'No $language text-to-speech voice is available. Open your device '
      'accessibility or spoken-content settings and enable a $language voice.';
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

Map<String, String>? chooseBestSpeechVoice(
  String language,
  SpeechVoiceGender gender,
  Iterable<Object?> installedVoices,
) {
  final preferredLocale = preferredSpeechLocale(language);
  final languageCode = preferredLocale.split('-').first.toLowerCase();
  final candidates = <Map<String, String>>[];
  for (final rawVoice in installedVoices) {
    if (rawVoice is! Map) continue;
    final name = rawVoice['name']?.toString() ?? '';
    final locale = (rawVoice['locale']?.toString() ?? '').replaceAll('_', '-');
    if (name.isEmpty || locale.toLowerCase().split('-').first != languageCode) continue;
    candidates.add({
      'name': name,
      'locale': locale,
      if (rawVoice['gender'] != null) 'gender': rawVoice['gender'].toString(),
      if (rawVoice['identifier'] != null)
        'identifier': rawVoice['identifier'].toString(),
      if (rawVoice['quality'] != null) 'quality': rawVoice['quality'].toString(),
    });
  }
  if (candidates.isEmpty) return null;
  candidates.sort((left, right) {
    int score(Map<String, String> voice) {
      final name = voice['name']!.toLowerCase();
      final locale = voice['locale']!.toLowerCase();
      final declaredGender = (voice['gender'] ?? '').toLowerCase();
      final markedFemale =
          declaredGender.contains('female') || name.contains('female') || name.contains('woman');
      final markedMale = declaredGender.contains('male') ||
          (!markedFemale && (name.contains('male') || name.contains('man')));
      var value = locale == preferredLocale.toLowerCase() ? 20 : 0;
      if (gender == SpeechVoiceGender.female) {
        if (markedFemale) value += 100;
        if (markedMale) value -= 100;
      } else {
        if (markedMale) value += 100;
        if (markedFemale) value -= 100;
      }
      final quality = (voice['quality'] ?? '').toLowerCase();
      if (quality.contains('enhanced') || quality == '2') value += 5;
      return value;
    }

    final scoreOrder = score(right).compareTo(score(left));
    if (scoreOrder != 0) return scoreOrder;
    final nameOrder = left['name']!.compareTo(right['name']!);
    return gender == SpeechVoiceGender.female ? nameOrder : -nameOrder;
  });
  return candidates.first;
}

class DeviceSpeech {
  DeviceSpeech({FlutterTts? engine}) : _engine = engine ?? FlutterTts();

  final FlutterTts _engine;
  bool _appleAudioConfigured = false;

  Future<void> _configurePlatformAudio() async {
    if (!Platform.isIOS || _appleAudioConfigured) return;
    await _engine.setSharedInstance(true).timeout(const Duration(seconds: 3));
    _appleAudioConfigured = true;
  }

  Future<String> _resolveLocale(String language) async {
    List<Object?> installed = const [];
    try {
      final result = await _engine.getLanguages.timeout(const Duration(seconds: 4));
      if (result is List) installed = result.cast<Object?>();
    } catch (_) {
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
    SpeechVoiceGender gender = SpeechVoiceGender.female,
    double speedFactor = 1,
  }) async {
    final content = text.trim();
    if (content.isEmpty) return;
    await _configurePlatformAudio();
    await _engine.stop().timeout(const Duration(seconds: 3));
    final locale = await _resolveLocale(language);
    final languageResult =
        await _engine.setLanguage(locale).timeout(const Duration(seconds: 4));
    if (languageResult == false || languageResult == 0) {
      throw SpeechVoiceUnavailableException(language);
    }
    try {
      final voices = await _engine.getVoices.timeout(const Duration(seconds: 4));
      if (voices is List) {
        final voice = chooseBestSpeechVoice(language, gender, voices.cast<Object?>());
        if (voice != null) {
          final selection = Platform.isIOS && voice['identifier'] != null
              ? {'identifier': voice['identifier']!}
              : {'name': voice['name']!, 'locale': voice['locale']!};
          await _engine.setVoice(selection).timeout(const Duration(seconds: 4));
        }
      }
    } catch (_) {
      // Keep the closest system voice selected by the resolved locale.
    }
    await _engine.setVolume(1).timeout(const Duration(seconds: 3));
    final speechRate = (0.42 * speedFactor).clamp(0.2, 0.84).toDouble();
    await _engine.setSpeechRate(speechRate).timeout(const Duration(seconds: 3));
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
