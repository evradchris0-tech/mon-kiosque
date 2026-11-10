enum PaymentMethod { cash, om }

enum PaymentStatus { confirmed, pending }

class PaymentLeg {
  PaymentLeg({
    required this.method,
    required this.amount,
    required this.status,
  });

  final PaymentMethod method;
  final double amount;
  PaymentStatus status;

  bool get isCash => method == PaymentMethod.cash;
  bool get isOm => method == PaymentMethod.om;
  bool get isConfirmed => status == PaymentStatus.confirmed;

  PaymentLeg copyWith({PaymentStatus? status}) =>
      PaymentLeg(method: method, amount: amount, status: status ?? this.status);
}

class Sale {
  Sale({
    required this.id,
    required this.createdAt,
    required this.amount,
    required this.legs,
    this.clientName,
    this.note,
  });

  final String id;
  final DateTime createdAt;
  final double amount;
  final List<PaymentLeg> legs;
  final String? clientName;
  final String? note;

  double get cashAmount =>
      legs.where((l) => l.isCash).fold(0.0, (s, l) => s + l.amount);

  double get omAmount =>
      legs.where((l) => l.isOm).fold(0.0, (s, l) => s + l.amount);

  bool get isHybrid => legs.length > 1;

  bool get isFullyConfirmed => legs.every((l) => l.isConfirmed);
}

class Client {
  Client({
    required this.id,
    required this.name,
    required this.totalSpent,
    required this.lastVisit,
  });

  final String id;
  final String name;
  final double totalSpent;
  final DateTime lastVisit;
}
