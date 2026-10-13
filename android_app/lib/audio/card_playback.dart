/// Preserve the September 2026 per-item fallback. Missing or broken transferred
/// audio must never prevent the phone from speaking either side of a card.
Future<void> playCardEntry({
  required String text,
  required String? source,
  required Future<void> Function(String source) playTransferred,
  required Future<void> Function(String text) speak,
}) async {
  if (text.trim().isEmpty) return;
  if (source != null && source.isNotEmpty) {
    try {
      await playTransferred(source);
      return;
    } catch (_) {
      // A missing download or unusable clip falls back for this entry only.
    }
  }
  await speak(text);
}
