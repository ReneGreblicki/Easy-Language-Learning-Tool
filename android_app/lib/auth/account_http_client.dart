import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

/// An old screen/outbox must never send requests with a newly selected account.
class AccountHttpClient extends http.BaseClient {
  AccountHttpClient({required this.accountId, required this.session, http.Client? inner})
      : _inner = inner ?? http.Client();
  final String accountId;
  final Session? Function() session;
  final http.Client _inner;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    final current = session();
    if (current == null || current.user.id != accountId) {
      throw const AuthException('The active account changed.');
    }
    request.headers['Authorization'] = 'Bearer ${current.accessToken}';
    return _inner.send(request);
  }
  @override
  void close() => _inner.close();
}
