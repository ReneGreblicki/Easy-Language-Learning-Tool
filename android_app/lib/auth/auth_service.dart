import 'package:supabase_flutter/supabase_flutter.dart';

class AuthService {
  AuthService(this.client);

  final SupabaseClient client;

  Stream<AuthState> get changes => client.auth.onAuthStateChange;
  Session? get session => client.auth.currentSession;

  Future<void> signIn({required String email, required String password}) async {
    await client.auth.signInWithPassword(email: email.trim(), password: password);
  }

  Future<void> register({
    required String username,
    required String email,
    required String password,
  }) async {
    await client.auth.signUp(
      email: email.trim(),
      password: password,
      data: {'username': username.trim()},
    );
  }

  Future<void> resetPassword(String email) =>
      client.auth.resetPasswordForEmail(email.trim());

  Future<void> signOut() => client.auth.signOut();
}
