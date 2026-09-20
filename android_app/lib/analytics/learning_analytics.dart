import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';

abstract interface class AnalyticsGateway {
  Future<Map<String, dynamic>> privacy();
  Future<Map<String, dynamic>> setEnabled(bool enabled);
  Future<String> record(Map<String, dynamic> event, int revision);
}

class SupabaseAnalyticsGateway implements AnalyticsGateway {
  SupabaseAnalyticsGateway(this.client);
  final SupabaseClient client;

  @override
  Future<Map<String, dynamic>> privacy() async =>
      Map<String, dynamic>.from(await client.rpc('learning_privacy') as Map);

  @override
  Future<Map<String, dynamic>> setEnabled(bool enabled) async =>
      Map<String, dynamic>.from(await client.rpc('set_learning_analytics',
          params: {'p_enabled': enabled}) as Map);

  @override
  Future<String> record(Map<String, dynamic> event, int revision) async =>
      await client.rpc('record_learning_activity', params: {
        'p_event_id': event['id'],
        'p_kind': event['kind'],
        'p_card_id': event['card_id'],
        'p_language': event['language'],
        'p_occurred_at': event['at'],
        'p_revision': revision,
      }) as String;
}

/// Optional analytics never blocks studying; retries retain the same event UUID.
class LearningAnalytics extends ChangeNotifier {
  LearningAnalytics({required this.gateway, required this.load, required this.save});

  final AnalyticsGateway gateway;
  final Future<String?> Function(String) load;
  final Future<void> Function(String, String?) save;
  bool enabled = false;
  bool ready = false;
  bool pendingDeletion = false;
  int _revision = 0;
  List<Map<String, dynamic>> _events = [];
  Future<void> _work = Future.value();
  bool _closed = false;

  Future<void> _serial(Future<void> Function() action) {
    final next = _work.then((_) async { if (!_closed) await action(); });
    _work = next.catchError((Object _) {});
    return next;
  }

  void _changed() { if (!_closed) notifyListeners(); }

  Future<void> initialize() => _serial(() async {
    final raw = await load('analytics:v1');
    if (raw != null) {
      final state = jsonDecode(raw) as Map<String, dynamic>;
      enabled = state['enabled'] == true;
      pendingDeletion = state['pending_deletion'] == true;
      _revision = state['revision'] as int? ?? 0;
      _events = (state['events'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    ready = true;
    _changed();
    await _flush();
  });

  Future<void> _persist() => save('analytics:v1', jsonEncode({
    'enabled': enabled, 'revision': _revision,
    'pending_deletion': pendingDeletion, 'events': _events,
  }));

  Future<void> setEnabled(bool value) {
    // Stop collection immediately, even if an older flush is awaiting a network response.
    if (!value) { enabled = false; pendingDeletion = true; _changed(); }
    return _serial(() async {
      if (!value) {
        _events.clear();
        await _persist();
        await _flush();
        return;
      }
      // Online acknowledgement is required before any optional collection starts.
      final state = await gateway.setEnabled(true);
      enabled = state['enabled'] == true;
      _revision = state['revision'] as int;
      pendingDeletion = false;
      _events.clear();
      await _persist();
      _changed();
    });
  }

  Future<void> record(String kind, String language, {String? cardId}) => _serial(() async {
    if (!ready || !enabled || pendingDeletion) return;
    _events.add({'id': const Uuid().v4(), 'kind': kind, 'language': language,
      'card_id': cardId, 'at': DateTime.now().toUtc().toIso8601String()});
    _events.removeWhere((e) => DateTime.parse(e['at'] as String)
        .isBefore(DateTime.now().toUtc().subtract(const Duration(days: 90))));
    if (_events.length > 25000) _events.removeAt(0);
    await _persist();
    await _flush();
  });

  Future<void> flush() => _serial(_flush);

  Future<void> _flush() async {
    try {
      if (pendingDeletion) {
        final state = await gateway.setEnabled(false);
        _revision = state['revision'] as int;
        pendingDeletion = false;
        enabled = false;
        _events.clear();
      } else {
        final state = await gateway.privacy();
        if (_closed) return;
        final remoteRevision = state['revision'] as int;
        if (remoteRevision != _revision) _events.clear();
        _revision = remoteRevision;
        if (!pendingDeletion) enabled = state['enabled'] == true;
      }
      while (enabled && !pendingDeletion && !_closed && _events.isNotEmpty) {
        final status = await gateway.record(_events.first, _revision);
        if (status == 'disabled' || status == 'stale') {
          enabled = false;
          _events.clear();
        } else {
          _events.removeAt(0);
        }
        await _persist();
      }
      await _persist();
      _changed();
    } on Exception {
      // Persisted events/deletion requests retry on refresh or next activity.
    }
  }

  @override
  void dispose() { _closed = true; super.dispose(); }
}
