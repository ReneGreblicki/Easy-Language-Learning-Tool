import 'package:easy_language_flashcards/errors/app_error.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  const fallback = 'The action failed. Try again.';

  test('converts host lookup failures into network instructions', () {
    final result = describeAppError(
      Exception(
        'ClientException with SocketException: Failed host lookup: '
        'project.supabase.co, uri=https://project.supabase.co/auth/v1/token',
      ),
      fallback: fallback,
    );

    expect(result, contains('Cannot reach the server'));
    expect(result, isNot(contains('supabase.co')));
    expect(result, isNot(contains('Exception')));
  });

  test('explains incorrect credentials', () {
    final result = describeAppError(
      const AuthException('Invalid login credentials'),
      fallback: fallback,
    );

    expect(result, contains('email address or password is incorrect'));
  });

  test('explains an unconfirmed account', () {
    final result = describeAppError(
      const AuthException('Email not confirmed'),
      fallback: fallback,
    );

    expect(result, contains('has not been confirmed'));
  });

  test('explains the rolling mobile generation allowance', () {
    final result = describeAppError(
      Exception('The 5,000-row mobile generation limit for the last 24 hours has been reached.'),
      fallback: fallback,
    );

    expect(result, contains('last 24 hours'));
    expect(result, contains('Try again'));
  });

  test('explains when phone generation is not configured', () {
    final result = describeAppError(
      Exception('Deck generation is not enabled yet.'),
      fallback: fallback,
    );

    expect(result, contains('has not been enabled'));
  });

  test('uses a safe fallback for unknown failures', () {
    final result = describeAppError(Exception('secret technical detail'), fallback: fallback);

    expect(result, fallback);
    expect(result, isNot(contains('secret technical detail')));
  });
}
