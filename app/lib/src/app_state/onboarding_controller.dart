import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class OnboardingController extends ChangeNotifier {
  OnboardingController._(this._prefs, this._seen);

  static const _key = 'onboarding_seen';
  final SharedPreferences _prefs;
  bool _seen;

  bool get seen => _seen;

  static Future<OnboardingController> load() async {
    final prefs = await SharedPreferences.getInstance();
    return OnboardingController._(prefs, prefs.getBool(_key) ?? false);
  }

  Future<void> markSeen() async {
    if (_seen) return;
    _seen = true;
    await _prefs.setBool(_key, true);
    notifyListeners();
  }

  Future<void> reset() async {
    _seen = false;
    await _prefs.remove(_key);
    notifyListeners();
  }
}
