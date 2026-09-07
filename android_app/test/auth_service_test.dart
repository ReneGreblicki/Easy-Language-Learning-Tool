import 'package:easy_language_flashcards/auth/auth_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('authentication callback uses the registered Android scheme', () {
    final callback = Uri.parse(AuthService.authCallbackUrl);

    expect(callback.scheme, 'com.renegreblicki.easylanguageflashcards');
    expect(callback.host, 'login-callback');
    expect(callback.path, '/');
  });
}
