import 'package:flutter/material.dart';

class SimulationController with ChangeNotifier {
  bool _isActive = false;
  int _currentStep = 0;

  bool get isActive => _isActive;
  int get currentStep => _currentStep;

  void toggle() {
    _isActive = !_isActive;
    if (!_isActive) _currentStep = 0;
    notifyListeners();
  }

  void nextStep() {
    _currentStep++;
    notifyListeners();
  }

  void reset() {
    _currentStep = 0;
    notifyListeners();
  }
}
