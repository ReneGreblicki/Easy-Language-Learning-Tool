import 'dart:async';
import 'dart:io';

import 'package:flutter_tts/flutter_tts.dart';
import 'package:flutter/services.dart';
import 'android_speech_engine.dart';

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

String speechErrorText(Object error) {
  if (error is PlatformException) {
    return 'Voice error (${error.code}): ${error.message ?? 'The phone could not start speech.'}';
  }
  if (error is TimeoutException) {
    return 'Voice playback timed out. Open Test voice and try another installed speech engine.';
  }
  if (error is SpeechVoiceUnavailableException) return error.toString();
  return 'Voice playback failed: $error';
}

String preferredSpeechLocale(String language) {
  final normalized = language.toLowerCase();
  if (normalized.contains('spanish')) return 'es-ES';
  if (normalized.contains('german')) return 'de-DE';
  if (normalized.contains('portuguese')) return 'pt-PT';
  if (normalized.contains('french')) return 'fr-FR';
  if (normalized.contains('italian')) return 'it-IT';
  if (normalized.contains('thai')) return 'th-TH';
  if (normalized.contains('polish')) return 'pl-PL';
  if (normalized.contains('dutch')) return 'nl-NL';
  if (normalized.contains('danish')) return 'da-DK';
  if (normalized.contains('croatian')) return 'hr-HR';
  if (normalized.contains('vietnamese')) return 'vi-VN';
  if (normalized.contains('chinese')) return 'zh-CN';
  if (normalized.contains('malayalam')) return 'ml-IN';
  if (normalized.contains('slovak')) return 'sk-SK';
  if (normalized.contains('russian')) return 'ru-RU';
  if (normalized.contains('norwegian')) return 'nb-NO';
  if (normalized.contains('korean')) return 'ko-KR';
  if (normalized.contains('hungarian')) return 'hu-HU';
  if (normalized.contains('swedish')) return 'sv-SE';
  if (normalized.contains('indonesian')) return 'id-ID';
  if (normalized.contains('japanese')) return 'ja-JP';
  if (normalized.contains('turkish')) return 'tr-TR';
  return 'en-US';
}

String speechLanguageCode(String locale) {
  final code = locale.replaceAll('_', '-').split('-').first.toLowerCase();
  return switch (code) {
    'no' || 'nn' => 'nb',
    'cmn' => 'zh',
    'in' => 'id',
    _ => code,
  };
}

String? chooseBestSpeechLocale(
  String language,
  Iterable<Object?> installedLocales,
) {
  final preferred = preferredSpeechLocale(language);
  final available = installedLocales
      .whereType<String>()
      .map((locale) => locale.replaceAll('_', '-'))
      .where((locale) => locale.isNotEmpty)
      .toList(growable: false);
  for (final locale in available) {
    if (locale.toLowerCase() == preferred.toLowerCase()) return locale;
  }
  final languageCode = speechLanguageCode(preferred);
  for (final locale in available) {
    if (speechLanguageCode(locale) == languageCode) return locale;
  }
  return null;
}

List<Map<String, String>> rankSpeechVoices(
  String language,
  SpeechVoiceGender gender,
  Iterable<Object?> installedVoices, {
  bool offlineOnly = false,
}) {
  final preferredLocale = preferredSpeechLocale(language);
  final languageCode = speechLanguageCode(preferredLocale);
  final candidates = <Map<String, String>>[];
  for (final rawVoice in installedVoices) {
    if (rawVoice is! Map) continue;
    final name = rawVoice['name']?.toString() ?? '';
    final locale = (rawVoice['locale']?.toString() ?? '').replaceAll('_', '-');
    if (name.isEmpty || speechLanguageCode(locale) != languageCode) {
      continue;
    }
    // Android lists voices whose data has not been installed yet.
    if ((rawVoice['features']?.toString() ?? '').toLowerCase().contains('notinstalled')) {
      continue;
    }
    final network = rawVoice['network_required']?.toString().toLowerCase();
    if (offlineOnly && network != 'false' && network != '0') continue;
    candidates.add({
      'name': name,
      'locale': locale,
      if (rawVoice['network_required'] != null)
        'network_required': rawVoice['network_required'].toString(),
      if (rawVoice['gender'] != null) 'gender': rawVoice['gender'].toString(),
      if (rawVoice['identifier'] != null)
        'identifier': rawVoice['identifier'].toString(),
      if (rawVoice['quality'] != null)
        'quality': rawVoice['quality'].toString(),
    });
  }
  if (candidates.isEmpty) return candidates;
  candidates.sort((left, right) {
    int score(Map<String, String> voice) {
      final name = voice['name']!.toLowerCase();
      final locale = voice['locale']!.toLowerCase();
      final declaredGender = (voice['gender'] ?? '').toLowerCase();
      final markedFemale =
          declaredGender.contains('female') ||
          name.contains('female') ||
          name.contains('woman');
      final markedMale =
          !markedFemale &&
          (declaredGender.contains('male') ||
              name.contains('male') ||
              RegExp(r'(^|[\s_-])man($|[\s_-])').hasMatch(name));
      var value = locale == preferredLocale.toLowerCase() ? 20 : 0;
      // Prefer a usable offline voice over a gender or regional match.
      if (voice['network_required'] == 'true' ||
          voice['network_required'] == '1') {
        value -= 1000;
      }
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
  return candidates;
}

Map<String, String>? chooseBestSpeechVoice(
  String language, SpeechVoiceGender gender, Iterable<Object?> installedVoices,
) {
  final candidates = rankSpeechVoices(language, gender, installedVoices);
  return candidates.isEmpty ? null : candidates.first;
}

class DeviceSpeech {
  DeviceSpeech({FlutterTts? engine}) : _engine = engine ?? (Platform.isAndroid ? AndroidSpeechEngine() : FlutterTts());

  final FlutterTts _engine;
  bool _appleAudioConfigured = false;
  int _requestVersion = 0;

  Future<void> _configurePlatformAudio() async {
    if (!Platform.isIOS || _appleAudioConfigured) return;
    await _engine.setSharedInstance(true).timeout(const Duration(seconds: 3));
    _appleAudioConfigured = true;
  }

  Future<String> _resolveLocale(String language) async {
    List<Object?> installed = const [];
    try {
      final result = await _engine.getLanguages.timeout(
        const Duration(seconds: 4),
      );
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
    final request = ++_requestVersion;
    final android = _engine is AndroidSpeechEngine;
    void checkCancelled() {
      if (request != _requestVersion) {
        throw PlatformException(code: 'TTS_CANCELLED', message: 'Speech was stopped.');
      }
    }
    await _configurePlatformAudio();
    await _engine.stop().timeout(const Duration(seconds: 3));
    List<Object?> voices = const [];
    try {
      final raw = await _engine.getVoices.timeout(const Duration(seconds: 4));
      if (raw is List) voices = raw.cast<Object?>();
    } catch (_) {
      if (android) rethrow;
    }
    checkCancelled();
    final ranked = rankSpeechVoices(language, gender, voices, offlineOnly: android);
    if (android && ranked.isEmpty) {
      throw PlatformException(code: 'TTS_OFFLINE_VOICE_UNAVAILABLE',
        message: 'No installed offline $language voice is available in this engine. '
          'Install its voice data in Android text-to-speech settings, or choose another engine in Test voice.');
    }
    final fallbackLocale = android ? null : await _resolveLocale(language);
    final choices = ranked.take(3).map<Map<String, String>?>((voice) => voice).toList();
    if (!android) choices.add(null);
    Object? lastError;
    for (final voice in choices) {
      checkCancelled();
      try {
        await _engine.stop().timeout(const Duration(seconds: 3));
        final locale = voice?['locale'] ?? fallbackLocale!;
        if (!android) {
          final result = await _engine.setLanguage(locale).timeout(const Duration(seconds: 4));
          if (result == false || result == 0) {
            throw SpeechVoiceUnavailableException(language);
          }
        }
        if (voice != null) {
          final selection = Platform.isIOS && voice['identifier'] != null
              ? {'identifier': voice['identifier']!}
              : {'name': voice['name']!, 'locale': voice['locale']!};
          final result = await _engine.setVoice(selection).timeout(const Duration(seconds: 4));
          if (result == false || result == 0) throw SpeechVoiceUnavailableException(language);
        }
        checkCancelled();
        await _engine.setVolume(1).timeout(const Duration(seconds: 3));
        await _engine.setSpeechRate((0.42 * speedFactor).clamp(0.2, 0.84).toDouble())
            .timeout(const Duration(seconds: 3));
        await _engine.awaitSpeakCompletion(awaitCompletion).timeout(const Duration(seconds: 3));
        checkCancelled();
        final played = await _engine.speak(content, focus: true).timeout(
          awaitCompletion ? Duration(seconds: (content.length ~/ 8).clamp(15, 120).toInt())
              : Duration(seconds: android ? 9 : 4));
        if (played == false || played == 0) throw SpeechVoiceUnavailableException(language);
        return;
      } catch (error) {
        checkCancelled();
        if (error is PlatformException && error.code == 'TTS_CANCELLED') rethrow;
        lastError = error;
      }
    }
    throw lastError ?? SpeechVoiceUnavailableException(language);
  }

  Future<Map<String, Object?>> diagnostics() async {
    if (!Platform.isAndroid) return {'engine': 'System voice', 'engines': <String>[]};
    final engine = await _engine.getDefaultEngine.timeout(const Duration(seconds: 3));
    final engines = await _engine.getEngines.timeout(const Duration(seconds: 3));
    return {'engine': engine?.toString() ?? 'Unknown',
      'engines': engines is List ? engines.whereType<String>().toList() : <String>[]};
  }

  Future<void> selectEngine(String engine) async {
    await _engine.setEngine(engine).timeout(const Duration(seconds: 10));
  }

  Future<void> stop() async {
    ++_requestVersion;
    await _engine.stop();
  }
}
