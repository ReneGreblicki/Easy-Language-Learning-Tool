import 'package:shared_preferences/shared_preferences.dart';

class AppPreferences {
  Future<bool> darkMode() async =>
      (await SharedPreferences.getInstance()).getBool('display:dark') ?? true;
  Future<void> saveDarkMode(bool dark) async {
    await (await SharedPreferences.getInstance()).setBool('display:dark', dark);
  }
  Future<List<String>> accounts() async =>
      (await SharedPreferences.getInstance()).getStringList('accounts:emails') ?? [];
  Future<void> remember(String email) async {
    final store = await SharedPreferences.getInstance();
    final values = {...?store.getStringList('accounts:emails'), email.trim()};
    await store.setStringList('accounts:emails', values.toList());
  }
  Future<void> forget(String email) async {
    final store = await SharedPreferences.getInstance();
    final values = store.getStringList('accounts:emails') ?? [];
    values.remove(email);
    await store.setStringList('accounts:emails', values);
  }
}
