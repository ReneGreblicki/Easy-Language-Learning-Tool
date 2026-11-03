import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

/// Bounds both connection/header waits and stalled response bodies.
class DeadlineHttpClient extends http.BaseClient {
  DeadlineHttpClient({http.Client? inner, this.requestTimeout = const Duration(seconds: 8)})
      : _inner = inner ?? http.Client();
  final http.Client _inner;
  final Duration requestTimeout;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final response = await _inner.send(request).timeout(requestTimeout);
    return http.StreamedResponse(response.stream.timeout(requestTimeout), response.statusCode,
      contentLength: response.contentLength, request: response.request,
      headers: response.headers, isRedirect: response.isRedirect,
      persistentConnection: response.persistentConnection, reasonPhrase: response.reasonPhrase);
  }
  @override
  void close() => _inner.close();
}

/// An old screen/outbox must never send requests with a newly selected account.
class AccountHttpClient extends DeadlineHttpClient {
  AccountHttpClient({required this.accountId, required this.session, super.inner,
    super.requestTimeout});
  final String accountId;
  final Session? Function() session;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    final current = session();
    if (current == null || current.user.id != accountId) {
      throw const AuthException('The active account changed.');
    }
    request.headers['Authorization'] = 'Bearer ${current.accessToken}';
    return super.send(request);
  }
}
