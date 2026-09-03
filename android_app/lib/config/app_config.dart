class AppConfig {
  const AppConfig({required this.supabaseUrl, required this.publishableKey});

  static const projectUrl = 'https://jmnsrikmqopdhmnkjmah.supabase.co';

  final String supabaseUrl;
  final String publishableKey;

  bool get isConfigured => supabaseUrl.isNotEmpty && publishableKey.isNotEmpty;

  static const fromEnvironment = AppConfig(
    supabaseUrl: String.fromEnvironment(
      'SUPABASE_URL',
      defaultValue: projectUrl,
    ),
    publishableKey: String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY'),
  );
}
