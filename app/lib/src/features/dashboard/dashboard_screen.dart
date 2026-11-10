import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'package:mon_kiosque/l10n/app_localizations.dart';
import '../../data/sales_controller.dart';
import '../../theme/app_colors.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppL10n.of(context)!;
    final sales = context.watch<SalesController>();

    final revenueToday = sales.revenueToday();
    final salesCount = sales.salesCountToday();
    final digital = sales.digitalRate();
    final series = sales.revenueLast7Days();
    final topClients = sales.clients.take(3).toList();

    return Scaffold(
      appBar: AppBar(title: Text(l10n.tabDashboard)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _KpiCard(
            title: l10n.dashboardTodayRevenue,
            value: _fmt(revenueToday),
            delta: '$salesCount ventes aujourd\'hui',
            icon: Icons.trending_up,
            color: AppColors.success,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _KpiCard(
                  title: l10n.dashboardDigitalRate,
                  value: '${(digital * 100).round()}%',
                  delta: digital >= 0.6 ? 'Bon niveau' : 'À améliorer',
                  icon: Icons.qr_code,
                  color: AppColors.orange,
                  compact: true,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _KpiCard(
                  title: l10n.dashboardUnpaid,
                  value: '12 000 F',
                  delta: '1 facture',
                  icon: Icons.schedule,
                  color: AppColors.warning,
                  compact: true,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _KpiCard(
            title: l10n.dashboardCreditScore,
            value: '${_scoreFrom(digital)} / 100',
            delta: 'Éligible M+6',
            icon: Icons.credit_score,
            color: AppColors.mokiViolet,
          ),
          const SizedBox(height: 24),
          const Text('Revenus (7 derniers jours)',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 16),
          _RevenueChart(series: series),
          const SizedBox(height: 24),
          if (topClients.isNotEmpty) ...[
            Text(l10n.dashboardTopClients,
                style: const TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 12),
            ...topClients.map(
              (c) => Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor:
                        AppColors.orange.withValues(alpha: 0.12),
                    child: Text(
                      c.name.isNotEmpty ? c.name[0] : '?',
                      style: const TextStyle(
                          color: AppColors.orange,
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                  title: Text(c.name,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('${_fmt(c.totalSpent)} sur 30 j'),
                  trailing: const Icon(Icons.chevron_right,
                      color: AppColors.slate),
                ),
              ),
            ),
          ],
          const SizedBox(height: 96),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/dashboard/payment'),
        backgroundColor: AppColors.orange,
        icon: const Icon(Icons.payments_outlined, color: Colors.white),
        label: const Text('Encaisser',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
      ),
    );
  }

  int _scoreFrom(double digital) => (55 + digital * 35).round().clamp(0, 100);

  String _fmt(double v) {
    final s = v.toStringAsFixed(0);
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
      buf.write(s[i]);
    }
    return '${buf.toString()} F';
  }
}

class _RevenueChart extends StatelessWidget {
  const _RevenueChart({required this.series});
  final List<double> series;

  @override
  Widget build(BuildContext context) {
    final maxVal = series.fold<double>(0, (m, v) => v > m ? v : m);
    return AspectRatio(
      aspectRatio: 1.7,
      child: BarChart(
        BarChartData(
          maxY: maxVal == 0 ? 100 : maxVal * 1.2,
          gridData: const FlGridData(show: false),
          titlesData: FlTitlesData(
            leftTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  const days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
                  final today = DateTime.now().weekday; // 1..7
                  final dayIdx = (today - 1 + (value.toInt() - 6) + 7) % 7;
                  if (value.toInt() < 0 || value.toInt() > 6) {
                    return const SizedBox();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(days[dayIdx],
                        style: const TextStyle(
                            color: AppColors.slate, fontSize: 10)),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          barGroups: [
            for (int i = 0; i < series.length; i++)
              BarChartGroupData(
                x: i,
                barRods: [
                  BarChartRodData(
                    toY: series[i],
                    color: AppColors.orange,
                    width: 18,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({
    required this.title,
    required this.value,
    required this.delta,
    required this.icon,
    required this.color,
    this.compact = false,
  });

  final String title;
  final String value;
  final String delta;
  final IconData icon;
  final Color color;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: color, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.slate),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              value,
              style: (compact
                      ? Theme.of(context).textTheme.titleLarge
                      : Theme.of(context).textTheme.headlineSmall)
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              delta,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: color, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}
