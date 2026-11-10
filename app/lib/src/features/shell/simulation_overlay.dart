import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../app_state/simulation_controller.dart';
import '../../theme/app_colors.dart';

class SimulationOverlay extends StatelessWidget {
  const SimulationOverlay({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final sim = context.watch<SimulationController>();
    if (!sim.isActive) return child;

    final scenes = [
      {'title': '1. Accueil', 'desc': 'Marie check ses ventes du matin.', 'path': '/dashboard'},
      {'title': '2. WhatsApp', 'desc': 'Le Proviseur envoie une commande.', 'path': '/chat'},
      {'title': '3. Capture', 'desc': 'Moki détecte l\'opportunité.', 'path': '/chat/1'},
      {'title': '4. Moki IA', 'desc': 'Génération de la facture en 2s.', 'path': '/moki'},
      {'title': '5. Encaissement', 'desc': 'Paiement Hybride (OM + Cash).', 'path': '/dashboard/payment'},
      {'title': '6. Victoire', 'desc': 'Score crédit up ! Marie est éligible.', 'path': '/dashboard'},
    ];

    final current = sim.currentStep % scenes.length;
    final scene = scenes[current];

    return Stack(
      children: [
        child,
        // Premium Demo Controller
        Positioned(
          bottom: 110,
          left: 16,
          right: 16,
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(milliseconds: 500),
            builder: (context, value, child) {
              return Transform.translate(
                offset: Offset(0, (1 - value) * 50),
                child: Opacity(
                  opacity: value,
                  child: child,
                ),
              );
            },
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.black,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 20, offset: const Offset(0, 10)),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: AppColors.orange.withValues(alpha: 0.2), shape: BoxShape.circle),
                    child: Text('${current + 1}', style: const TextStyle(color: AppColors.orange, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(scene['title']!, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                        const SizedBox(height: 2),
                        Text(scene['desc']!, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () {
                      sim.nextStep();
                      final next = (sim.currentStep) % scenes.length;
                      context.go(scenes[next]['path']!);
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.orange,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      elevation: 0,
                    ),
                    child: const Text('SUIVANT'),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white54, size: 20),
                    onPressed: () => sim.toggle(),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
