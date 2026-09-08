import 'package:easy_language_flashcards/audio/playback_settings.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('speed adjustment has normal speed at zero and safe end points', () {
    expect(playbackFactorForAdjustment(-2), 0.5);
    expect(playbackFactorForAdjustment(0), 1);
    expect(playbackFactorForAdjustment(2), 2);
  });

  test('default break is among the selectable pause options', () {
    expect(playbackPauseOptions, contains(0.5));
  });
}
