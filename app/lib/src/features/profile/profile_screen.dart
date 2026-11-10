import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mon_kiosque/l10n/app_localizations.dart';
import '../../app_state/locale_controller.dart';
import '../../app_state/onboarding_controller.dart';
import '../../app_state/simulation_controller.dart';
import '../../theme/app_colors.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppL10n.of(context)!;
    final localeCtrl = context.watch<LocaleController>();
    final onboardingCtrl = context.read<OnboardingController>();
    final simCtrl = context.watch<SimulationController>();

    return Scaffold(
      appBar: AppBar(title: Text(l10n.tabProfile)),
      body: ListView(
        children: [
          _Header(),
          const SizedBox(height: 8),
          _SectionTitle(label: l10n.profileLanguage),
          ListTile(
            title: Text(l10n.languageFrench),
            trailing: localeCtrl.locale.languageCode == 'fr'
                ? const Icon(Icons.check, color: AppColors.orange)
                : null,
            onTap: () => localeCtrl.set(const Locale('fr')),
          ),
          ListTile(
            title: Text(l10n.languageEnglish),
            trailing: localeCtrl.locale.languageCode == 'en'
                ? const Icon(Icons.check, color: AppColors.orange)
                : null,
            onTap: () => localeCtrl.set(const Locale('en')),
          ),
          const Divider(),
          _SectionTitle(label: 'Mode Démo (Hackathon)'),
          SwitchListTile(
            title: const Text('Activer le mode simulation'),
            subtitle: const Text('Affiche les contrôles de démo jury'),
            value: simCtrl.isActive,
            onChanged: (v) => simCtrl.toggle(),
            activeThumbColor: AppColors.mokiViolet,
          ),
          const Divider(),
          _SectionTitle(label: l10n.profileSubscription),
          ListTile(
            leading: const Icon(Icons.card_membership_outlined),
            title: Text(l10n.planStarter),
            subtitle: const Text('2 900 FCFA / mois'),
            trailing: const Icon(Icons.chevron_right),
          ),
          _SectionTitle(label: l10n.profileSecurity),
          const ListTile(
            leading: Icon(Icons.lock_outline),
            title: Text('PIN & authentification'),
            trailing: Icon(Icons.chevron_right),
          ),
          _SectionTitle(label: l10n.profileSupport),
          const ListTile(
            leading: Icon(Icons.help_outline),
            title: Text('Centre d\'aide'),
            trailing: Icon(Icons.chevron_right),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.refresh, color: AppColors.slate),
            title: const Text('Rejouer l\'onboarding (debug)'),
            onTap: () => onboardingCtrl.reset(),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      color: AppColors.white,
      child: Row(
        children: [
          const CircleAvatar(
            radius: 28,
            backgroundColor: AppColors.orangeLight,
            child: Text('MN', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Marie Nkoulou',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              const Text('Snack « Chez Marie » — Essos, Yaoundé',
                  style: TextStyle(color: AppColors.slate, fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
      child: Text(
        label.toUpperCase(),
        style: const TextStyle(
          color: AppColors.slate,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.1,
        ),
      ),
    );
  }
}
