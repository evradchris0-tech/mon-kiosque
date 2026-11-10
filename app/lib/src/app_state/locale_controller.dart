import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocaleController extends ChangeNotifier {
  LocaleController._(this._prefs, this._locale);

  static const _key = 'locale';
  final SharedPreferences _prefs;
  Locale _locale;

  Locale get locale => _locale;

  static Future<LocaleController> load() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_key) ?? 'fr';
    return LocaleController._(prefs, Locale(code));
  }

  Future<void> set(Locale locale) async {
    if (_locale == locale) return;
    _locale = locale;
    await _prefs.setString(_key, locale.languageCode);
    notifyListeners();
  }
}
