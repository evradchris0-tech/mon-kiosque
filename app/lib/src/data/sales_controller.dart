import 'dart:math';
import 'package:flutter/foundation.dart';

import 'models.dart';

/// In-memory sales store seeded with Marie Nkoulou's recent history.
/// Demo-grade: lives for the session, no persistence required for the prototype.
class SalesController extends ChangeNotifier {
  SalesController() {
    _seed();
  }

  final List<Sale> _sales = [];
  final List<Client> _clients = [];
  int _seq = 0;

  List<Sale> get sales => List.unmodifiable(_sales);
  List<Client> get clients => List.unmodifiable(_clients);

  String _nextId() {
    _seq += 1;
    final n = _seq.toString().padLeft(3, '0');
    return 'VTE-2026-$n';
  }

  // ---- Aggregates used by the Dashboard ----

  double revenueToday() {
    final now = DateTime.now();
    return _sales
        .where((s) =>
            s.createdAt.year == now.year &&
            s.createdAt.month == now.month &&
            s.createdAt.day == now.day)
        .fold(0.0, (sum, s) => sum + s.amount);
  }

  /// Digital tracking rate over the last 30 days.
  double digitalRate() {
    final cutoff = DateTime.now().subtract(const Duration(days: 30));
    final recent = _sales.where((s) => s.createdAt.isAfter(cutoff));
    final total = recent.fold(0.0, (s, x) => s + x.amount);
    if (total == 0) return 0;
    final om = recent.fold(0.0, (s, x) => s + x.omAmount);
    return om / total;
  }

  /// Last 7 days revenue series — Mon..Sun aligned on today.
  List<double> revenueLast7Days() {
    final now = DateTime.now();
    return List.generate(7, (i) {
      final day = now.subtract(Duration(days: 6 - i));
      return _sales
          .where((s) =>
              s.createdAt.year == day.year &&
              s.createdAt.month == day.month &&
              s.createdAt.day == day.day)
          .fold(0.0, (sum, s) => sum + s.amount);
    });
  }

  int salesCountToday() {
    final now = DateTime.now();
    return _sales
        .where((s) =>
            s.createdAt.year == now.year &&
            s.createdAt.month == now.month &&
            s.createdAt.day == now.day)
        .length;
  }

  // ---- Mutations ----

  Sale recordSale({
    required double amount,
    required double cashAmount,
    required double omAmount,
    String? clientName,
    String? note,
  }) {
    final legs = <PaymentLeg>[];
    if (cashAmount > 0) {
      legs.add(PaymentLeg(
        method: PaymentMethod.cash,
        amount: cashAmount,
        status: PaymentStatus.confirmed,
      ));
    }
    if (omAmount > 0) {
      legs.add(PaymentLeg(
        method: PaymentMethod.om,
        amount: omAmount,
        status: PaymentStatus.pending,
      ));
    }
    final sale = Sale(
      id: _nextId(),
      createdAt: DateTime.now(),
      amount: amount,
      legs: legs,
      clientName: clientName,
      note: note,
    );
    _sales.insert(0, sale);
    notifyListeners();
    return sale;
  }

  /// Marks the OM leg(s) of a sale as confirmed (callback simulation).
  void confirmOmLeg(String saleId) {
    final idx = _sales.indexWhere((s) => s.id == saleId);
    if (idx == -1) return;
    final sale = _sales[idx];
    final updatedLegs = sale.legs
        .map((l) => l.isOm ? l.copyWith(status: PaymentStatus.confirmed) : l)
        .toList();
    _sales[idx] = Sale(
      id: sale.id,
      createdAt: sale.createdAt,
      amount: sale.amount,
      legs: updatedLegs,
      clientName: sale.clientName,
      note: sale.note,
    );
    notifyListeners();
  }

  // ---- Seed: Marie Nkoulou's last 30 days ----

  void _seed() {
    final rng = Random(42);
    final now = DateTime.now();
    final clientNames = [
      'Mme Biya', 'Lycée Technique', 'Paul (livraison)', 'Bureau Essos',
      'Mme Ngono', 'M. Kamto', 'Cantine Mvog-Ada', 'Famille Atangana',
    ];

    for (int d = 30; d >= 1; d--) {
      final day = now.subtract(Duration(days: d));
      // 8 to 16 sales per day.
      final salesPerDay = 8 + rng.nextInt(9);
      for (int i = 0; i < salesPerDay; i++) {
        final hour = 8 + rng.nextInt(12);
        final minute = rng.nextInt(60);
        final ts = DateTime(day.year, day.month, day.day, hour, minute);

        final pick = rng.nextDouble();
        // Realistic basket: 1k–25k FCFA, skewed toward 2–8k.
        final amount = (1000 + rng.nextInt(24) * 1000).toDouble();

        final List<PaymentLeg> legs;
        if (pick < 0.55) {
          // 55% cash only
          legs = [
            PaymentLeg(
                method: PaymentMethod.cash,
                amount: amount,
                status: PaymentStatus.confirmed),
          ];
        } else if (pick < 0.85) {
          // 30% OM only
          legs = [
            PaymentLeg(
                method: PaymentMethod.om,
                amount: amount,
                status: PaymentStatus.confirmed),
          ];
        } else {
          // 15% hybrid
          final cashPart = ((amount / 1000) * (0.3 + rng.nextDouble() * 0.4))
                  .round() *
              1000.0;
          final omPart = amount - cashPart;
          legs = [
            PaymentLeg(
                method: PaymentMethod.cash,
                amount: cashPart,
                status: PaymentStatus.confirmed),
            PaymentLeg(
                method: PaymentMethod.om,
                amount: omPart,
                status: PaymentStatus.confirmed),
          ];
        }

        _sales.add(Sale(
          id: _nextId(),
          createdAt: ts,
          amount: amount,
          legs: legs,
          clientName: clientNames[rng.nextInt(clientNames.length)],
        ));
      }
    }

    _sales.sort((a, b) => b.createdAt.compareTo(a.createdAt));

    // Build client aggregates.
    final byName = <String, List<Sale>>{};
    for (final s in _sales) {
      if (s.clientName == null) continue;
      byName.putIfAbsent(s.clientName!, () => []).add(s);
    }
    int idx = 0;
    byName.forEach((name, list) {
      idx += 1;
      _clients.add(Client(
        id: 'C-${idx.toString().padLeft(3, '0')}',
        name: name,
        totalSpent: list.fold(0.0, (s, x) => s + x.amount),
        lastVisit: list.first.createdAt,
      ));
    });
    _clients.sort((a, b) => b.totalSpent.compareTo(a.totalSpent));
  }
}
