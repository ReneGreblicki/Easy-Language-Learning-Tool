import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Android uses a public-API bridge with initialization/start deadlines and
/// callbacks installed before queued calls are released. Apple retains FlutterTts.
class AndroidSpeechEngine extends FlutterTts {
  static const channel = MethodChannel('easy_language_learning_tool/native_speech');

  Future<void> installVoiceData() => channel.invokeMethod<void>('installVoiceData');
  Future<void> refreshVoiceData() => channel.invokeMethod<void>('refreshVoiceData');

  @override
  Future<dynamic> get getLanguages => channel.invokeMethod('getLanguages');
  @override
  Future<dynamic> get getVoices => channel.invokeMethod('getVoices');
  @override
  Future<dynamic> get getDefaultEngine => channel.invokeMethod('getDefaultEngine');
  @override
  Future<dynamic> get getEngines => channel.invokeMethod('getEngines');
  @override
  Future<dynamic> setEngine(String engine) => channel.invokeMethod('setEngine', engine);
  @override
  Future<dynamic> setLanguage(String language) => channel.invokeMethod('setLanguage', language);
  @override
  Future<dynamic> setVoice(Map<String, String> voice) => channel.invokeMethod('setVoice', voice);
  @override
  Future<dynamic> setVolume(double volume) => channel.invokeMethod('setVolume', volume);
  @override
  Future<dynamic> setSpeechRate(double rate) => channel.invokeMethod('setSpeechRate', rate);
  @override
  Future<dynamic> awaitSpeakCompletion(bool awaitCompletion) => channel.invokeMethod('awaitSpeakCompletion', awaitCompletion);
  @override
  Future<dynamic> speak(String text, {bool focus = false}) =>
      channel.invokeMethod('speak', {'text': text, 'focus': focus});
  @override
  Future<dynamic> stop() => channel.invokeMethod('stop');
}
