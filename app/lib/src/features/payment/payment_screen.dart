import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../data/models.dart';
import '../../data/sales_controller.dart';
import '../../theme/app_colors.dart';

enum _Mode { om, cash, hybrid }

class PaymentScreen extends StatefulWidget {
  const PaymentScreen({super.key});

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  final _amountCtrl = TextEditingController();
  final _cashCtrl = TextEditingController();
  final _omCtrl = TextEditingController();

  _Mode _mode = _Mode.om;
  Sale? _pendingSale;

  @override
  void dispose() {
    _amountCtrl.dispose();
    _cashCtrl.dispose();
    _omCtrl.dispose();
    super.dispose();
  }

  double get _total => double.tryParse(_amountCtrl.text) ?? 0;
  double get _cash => double.tryParse(_cashCtrl.text) ?? 0;
  double get _om => double.tryParse(_omCtrl.text) ?? 0;

  bool get _isValid {
    if (_total <= 0) return false;
    switch (_mode) {
      case _Mode.om:
      case _Mode.cash:
        return true;
      case _Mode.hybrid:
        return _cash > 0 && _om > 0 && (_cash + _om - _total).abs() < 1;
    }
  }

  void _onHybridChange(String val, {required bool isCash}) {
    if (_total <= 0) return;
    final current = double.tryParse(val) ?? 0;
    if (current < 0 || current > _total) return;
    final other = (_total - current).clamp(0, _total).toDouble();
    if (isCash) {
      _omCtrl.text = other.toStringAsFixed(0);
    } else {
      _cashCtrl.text = other.toStringAsFixed(0);
    }
    setState(() {});
  }

  void _validate() {
    FocusScope.of(context).unfocus();
    final sales = context.read<SalesController>();
    final double cash;
    final double om;
    switch (_mode) {
      case _Mode.cash:
        cash = _total;
        om = 0;
        break;
      case _Mode.om:
        cash = 0;
        om = _total;
        break;
      case _Mode.hybrid:
        cash = _cash;
        om = _om;
        break;
    }
    final sale = sales.recordSale(
      amount: _total,
      cashAmount: cash,
      omAmount: om,
    );

    if (om == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Vente ${sale.id} enregistrée — ${_fmt(_total)} cash'),
          backgroundColor: AppColors.success,
        ),
      );
      Navigator.pop(context);
      return;
    }

    setState(() => _pendingSale = sale);
    // Simulate Orange Money confirmation callback.
    Future.delayed(const Duration(seconds: 3), () {
      if (!mounted || _pendingSale == null) return;
      sales.confirmOmLeg(sale.id);
      final wasHybrid = cash > 0;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(wasHybrid
              ? '${_fmt(om)} OM reçu — vente ${sale.id} bouclée (${_fmt(_total)})'
              : '${_fmt(om)} OM reçu — vente ${sale.id}'),
          backgroundColor: AppColors.success,
        ),
      );
      Navigator.pop(context);
    });
  }

  String _fmt(double v) {
    final s = v.toStringAsFixed(0);
    // Thousands separator with narrow space.
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
      buf.write(s[i]);
    }
    return '${buf.toString()} F';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Encaisser')),
      body: _pendingSale != null ? _buildQR(_pendingSale!) : _buildForm(),
    );
  }

  Widget _buildQR(Sale sale) {
    final omLeg = sale.legs.firstWhere((l) => l.isOm);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(sale.id,
                style: const TextStyle(color: AppColors.slate, fontSize: 13)),
            const SizedBox(height: 4),
            const Text('Scanner pour payer',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Text('${_fmt(omLeg.amount)} via Orange Money',
                style: const TextStyle(color: AppColors.slate)),
            if (sale.isHybrid) ...[
              const SizedBox(height: 4),
              Text('Déjà reçu en liquide : ${_fmt(sale.cashAmount)}',
                  style: const TextStyle(
                      color: AppColors.success, fontWeight: FontWeight.w600)),
            ],
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: AppColors.cloud),
              ),
              child: QrImageView(
                data:
                    'om://pay?merchant=CHEZ_MARIE&amount=${omLeg.amount.toStringAsFixed(0)}&sale=${sale.id}',
                version: QrVersions.auto,
                size: 240,
                backgroundColor: Colors.white,
                eyeStyle: const QrEyeStyle(
                    eyeShape: QrEyeShape.square, color: AppColors.black),
                dataModuleStyle: const QrDataModuleStyle(
                    dataModuleShape: QrDataModuleShape.square,
                    color: AppColors.orange),
              ),
            ),
            const SizedBox(height: 32),
            const CircularProgressIndicator(color: AppColors.orange),
            const SizedBox(height: 12),
            const Text('En attente du paiement…',
                style: TextStyle(color: AppColors.slate)),
          ],
        ),
      ),
    );
  }

  Widget _buildForm() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('Montant total',
            style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        TextField(
          controller: _amountCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
          decoration: InputDecoration(
            suffixText: 'FCFA',
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.cloud),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.cloud),
            ),
          ),
          onChanged: (_) {
            if (_mode == _Mode.hybrid) {
              _cashCtrl.clear();
              _omCtrl.clear();
            }
            setState(() {});
          },
        ),
        const SizedBox(height: 24),
        const Text('Mode de paiement',
            style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _ModeButton(
                title: 'Orange Money',
                icon: Icons.phone_android,
                isSelected: _mode == _Mode.om,
                onTap: () => setState(() => _mode = _Mode.om),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _ModeButton(
                title: 'Cash',
                icon: Icons.payments_outlined,
                isSelected: _mode == _Mode.cash,
                onTap: () => setState(() => _mode = _Mode.cash),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _ModeButton(
                title: 'Hybride',
                icon: Icons.pie_chart_outline,
                isSelected: _mode == _Mode.hybrid,
                onTap: () => setState(() => _mode = _Mode.hybrid),
              ),
            ),
          ],
        ),
        if (_mode == _Mode.hybrid) ...[
          const SizedBox(height: 20),
          _HybridBlock(
            total: _total,
            cashCtrl: _cashCtrl,
            omCtrl: _omCtrl,
            onCashChange: (v) => _onHybridChange(v, isCash: true),
            onOmChange: (v) => _onHybridChange(v, isCash: false),
            cash: _cash,
            om: _om,
          ),
        ],
        const SizedBox(height: 36),
        FilledButton(
          onPressed: _isValid ? _validate : null,
          child: Text(_mode == _Mode.cash
              ? 'Enregistrer la vente'
              : 'Générer le QR Orange Money'),
        ),
        const SizedBox(height: 8),
        const Text(
          'Moki confirme avant d\'agir : Interprétation → Vérification → Confirmation.',
          style: TextStyle(color: AppColors.slate, fontSize: 12),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({
    required this.title,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  final String title;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.orange : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: isSelected ? AppColors.orange : AppColors.cloud),
        ),
        child: Column(
          children: [
            Icon(icon, color: isSelected ? Colors.white : AppColors.graphite),
            const SizedBox(height: 6),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: isSelected ? Colors.white : AppColors.graphite,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HybridBlock extends StatelessWidget {
  const _HybridBlock({
    required this.total,
    required this.cashCtrl,
    required this.omCtrl,
    required this.onCashChange,
    required this.onOmChange,
    required this.cash,
    required this.om,
  });

  final double total;
  final TextEditingController cashCtrl;
  final TextEditingController omCtrl;
  final ValueChanged<String> onCashChange;
  final ValueChanged<String> onOmChange;
  final double cash;
  final double om;

  @override
  Widget build(BuildContext context) {
    final sum = cash + om;
    final ratio = total > 0 ? (sum / total).clamp(0.0, 1.0) : 0.0;
    final delta = total - sum;
    final balanced = total > 0 && delta.abs() < 1;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.orange.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.orange.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Répartition du paiement',
              style: TextStyle(
                  fontWeight: FontWeight.w700, color: AppColors.orangeDark)),
          const SizedBox(height: 4),
          const Text('Le client paye une partie en liquide, le reste via OM.',
              style: TextStyle(fontSize: 12, color: AppColors.slate)),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _LegField(
                  label: 'Cash',
                  controller: cashCtrl,
                  onChanged: onCashChange,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _LegField(
                  label: 'Orange Money',
                  controller: omCtrl,
                  onChanged: onOmChange,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 8,
              backgroundColor: AppColors.cloud,
              color: balanced ? AppColors.success : AppColors.warning,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            balanced
                ? 'Répartition équilibrée ✓'
                : (total == 0
                    ? 'Saisis d\'abord le montant total.'
                    : (delta > 0
                        ? 'Manque ${delta.toStringAsFixed(0)} F'
                        : 'Excède de ${(-delta).toStringAsFixed(0)} F')),
            style: TextStyle(
              fontSize: 12,
              color: balanced ? AppColors.success : AppColors.warning,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _LegField extends StatelessWidget {
  const _LegField({
    required this.label,
    required this.controller,
    required this.onChanged,
  });

  final String label;
  final TextEditingController controller;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 12, color: AppColors.slate)),
        TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style:
              const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          decoration: const InputDecoration(
            suffixText: 'F',
            border: UnderlineInputBorder(),
          ),
          onChanged: onChanged,
        ),
      ],
    );
  }
}
