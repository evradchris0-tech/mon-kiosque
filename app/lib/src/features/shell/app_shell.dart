import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mon_kiosque/l10n/app_localizations.dart';
import '../../theme/app_colors.dart';
import 'simulation_overlay.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    final l10n = AppL10n.of(context)!;
    return SimulationOverlay(
      child: Scaffold(
        body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (i) => navigationShell.goBranch(
          i,
          initialLocation: i == navigationShell.currentIndex,
        ),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.chat_bubble_outline),
            selectedIcon: const Icon(Icons.chat_bubble, color: AppColors.orange),
            label: l10n.tabChat,
          ),
          NavigationDestination(
            icon: const Icon(Icons.auto_awesome_outlined),
            selectedIcon: const Icon(Icons.auto_awesome, color: AppColors.orange),
            label: l10n.tabMoki,
          ),
          NavigationDestination(
            icon: const Icon(Icons.insights_outlined),
            selectedIcon: const Icon(Icons.insights, color: AppColors.orange),
            label: l10n.tabDashboard,
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline),
            selectedIcon: const Icon(Icons.person, color: AppColors.orange),
            label: l10n.tabProfile,
          ),
        ],
      ),
    ),);
  }
}
