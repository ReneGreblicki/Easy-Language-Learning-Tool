double playbackFactorForAdjustment(double adjustment) {
  final value = adjustment.clamp(-2, 2).toDouble();
  return value <= 0 ? 1 + value * 0.25 : 1 + value * 0.5;
}

const playbackPauseOptions = <double>[0, 0.25, 0.5, 0.75, 1, 1.5, 2];
