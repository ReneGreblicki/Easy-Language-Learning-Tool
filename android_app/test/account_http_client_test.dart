import 'package:easy_language_flashcards/auth/account_http_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

Session session(String id, String token) => Session(
  accessToken: token, tokenType: 'bearer', user: User(id: id,
    appMetadata: {}, userMetadata: {}, aud: 'authenticated', createdAt: '2026-09-20T00:00:00Z'));
void main() {
  test('old account cannot send with a new session; refreshed token is used', () async {
    Session? active = session('alice', 'first');
    var requests = 0;
    final client = AccountHttpClient(accountId: 'alice', session: () => active,
      inner: MockClient((request) async {
        requests++;
        expect(request.headers['Authorization'], 'Bearer refreshed');
        return http.Response('{}', 200);
      }));
    active = session('alice', 'refreshed');
    await client.get(Uri.parse('https://example.invalid'));
    active = session('bob', 'other');
    await expectLater(client.get(Uri.parse('https://example.invalid')), throwsA(isA<AuthException>()));
    active = null;
    await expectLater(client.get(Uri.parse('https://example.invalid')), throwsA(isA<AuthException>()));
    expect(requests, 1);
    client.close();
  });
}
