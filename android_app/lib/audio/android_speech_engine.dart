import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Android uses a public-API bridge with initialization/start deadlines and
/// callbacks installed before queued calls are released. Apple retains FlutterTts.
class AndroidSpeechEngine extends FlutterTts {
  static const channel = MethodChannel('easy_language_learning_tool/native_speech');

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
  Future<dynamic> setLanguage(String locale) => channel.invokeMethod('setLanguage', locale);
  @override
  Future<dynamic> setVoice(Map<String, String> voice) => channel.invokeMethod('setVoice', voice);
  @override
  Future<dynamic> setVolume(double value) => channel.invokeMethod('setVolume', value);
  @override
  Future<dynamic> setSpeechRate(double value) => channel.invokeMethod('setSpeechRate', value);
  @override
  Future<dynamic> awaitSpeakCompletion(bool value) => channel.invokeMethod('awaitSpeakCompletion', value);
  @override
  Future<dynamic> speak(String text, {bool focus = false}) =>
      channel.invokeMethod('speak', {'text': text, 'focus': focus});
  @override
  Future<dynamic> stop() => channel.invokeMethod('stop');
}
