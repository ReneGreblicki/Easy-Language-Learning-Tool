import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

String describeAppError(
  Object error, {
  required String fallback,
}) {
  final message = error.toString().toLowerCase();

  if (error is SocketException ||
      error is http.ClientException ||
      message.contains('failed host lookup') ||
      message.contains('socketexception') ||
      message.contains('network is unreachable') ||
      message.contains('connection refused') ||
      message.contains('connection reset')) {
    return 'Cannot reach the server. Check your internet connection, disable any VPN, '
        'Private DNS, or network blocker, and try again.';
  }
  if (error is TimeoutException || message.contains('timed out') || message.contains('timeout')) {
    return 'The server took too long to respond. Check your connection and try again.';
  }
  if (message.contains('invalid login credentials') ||
      message.contains('invalid email or password')) {
    return 'The email address or password is incorrect. Check both fields and try again.';
  }
  if (message.contains('email not confirmed')) {
    return 'Your email address has not been confirmed. Open the confirmation email, then try again.';
  }
  if (message.contains('user already registered') || message.contains('already been registered')) {
    return 'An account already exists for this email address. Sign in or use Forgot password.';
  }
  if (message.contains('password should be') ||
      message.contains('weak_password') ||
      message.contains('password is too short')) {
    return 'The password is too weak. Use at least 8 characters with a mixture of letters and numbers.';
  }
  if (message.contains('invalid email') || message.contains('email_address_invalid')) {
    return 'Enter a valid email address, for example name@example.com.';
  }
  if (message.contains('rate limit') ||
      message.contains('too many requests') ||
      message.contains('over_email_send_rate_limit') ||
      message.contains('429')) {
    return 'Too many attempts were made. Wait a few minutes before trying again.';
  }
  if (message.contains('signup') && message.contains('disabled')) {
    return 'New account registration is temporarily unavailable. Try signing in or contact support.';
  }
  if (message.contains('captcha')) {
    return 'Account verification was not completed. Retry the action and complete the verification step.';
  }
  if (message.contains('jwt expired') ||
      message.contains('invalid jwt') ||
      message.contains('session') && message.contains('expired')) {
    return 'Your session has expired. Sign out, sign in again, and retry the action.';
  }
  if (message.contains('permission denied') ||
      message.contains('row-level security') ||
      message.contains('42501')) {
    return 'This account does not have permission to access that item. Refresh or sign in again.';
  }
  if (message.contains('not found') || message.contains('deck not found')) {
    return 'The requested item is no longer available. Refresh the deck list and try again.';
  }
  if (error is FormatException || message.contains('invalid format')) {
    return 'The received data is not in a supported format. Refresh it from the desktop app.';
  }
  if (message.contains('storage') &&
      (message.contains('full') || message.contains('space'))) {
    return 'There is not enough free storage on this phone. Free some space and try again.';
  }
  if (error is HttpException || message.contains('could not download')) {
    return 'The file could not be downloaded. Check your connection and try again.';
  }
  if (error is AuthException) {
    return 'Authentication failed. Check your account details and try again.';
  }
  if (error is PostgrestException || message.contains('postgrest')) {
    return 'The synchronized data could not be accessed. Refresh and try again.';
  }
  if (message.contains('500') ||
      message.contains('502') ||
      message.contains('503') ||
      message.contains('service unavailable')) {
    return 'The server is temporarily unavailable. Wait a few minutes and try again.';
  }
  return fallback;
}
