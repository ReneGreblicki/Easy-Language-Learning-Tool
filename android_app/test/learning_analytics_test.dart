import 'dart:convert';
import 'package:easy_language_flashcards/analytics/learning_analytics.dart';
import 'package:flutter_test/flutter_test.dart';

class Gateway implements AnalyticsGateway {
  bool online = true, enabled = false;
  int revision = 0;
  final events = <Map<String,dynamic>>[];
  Map<String,dynamic> state() {
    if (!online) throw Exception('offline');
    return {'enabled':enabled,'revision':revision};
  }
  @override
  Future<Map<String,dynamic>> privacy() async => state();
  @override
  Future<Map<String,dynamic>> setEnabled(bool value) async {
    state(); if (enabled != value) revision++;
    enabled=value; return state();
  }
  @override
  Future<String> record(Map<String,dynamic> event, int revision) async {
    state(); events.add({...event}); return 'ok';
  }
}
void main() {
  test('off by default; offline card IDs persist and opt-out erases queue', () async {
    final gateway=Gateway();
    final storage=<String,String>{};
    final analytics=LearningAnalytics(gateway:gateway,
      load:(key) async => storage[key], save:(key,value) async { if(value!=null) storage[key]=value; });
    await analytics.initialize();
    await analytics.record('card_opened','German',cardId:'card-1');
    expect(gateway.events,isEmpty);
    await analytics.setEnabled(true);
    gateway.online=false;
    await analytics.record('card_opened','German',cardId:'card-1');
    expect((jsonDecode(storage['analytics:v1']!)['events'] as List).single['card_id'],'card-1');
    gateway.online=true;
    await analytics.flush();
    expect(gateway.events.single['card_id'],'card-1');
    gateway.online=false;
    await analytics.record('card_opened','German',cardId:'card-2');
    await analytics.setEnabled(false);
    expect(analytics.enabled,false);
    expect(analytics.pendingDeletion,true);
    expect(jsonDecode(storage['analytics:v1']!)['events'],isEmpty);
    gateway.online=true;
    await analytics.flush();
    expect(analytics.pendingDeletion,false);
    expect(gateway.enabled,false);
    expect(gateway.events,hasLength(1));
    analytics.dispose();
  });
}
