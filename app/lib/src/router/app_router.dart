import 'package:go_router/go_router.dart';

import '../app_state/locale_controller.dart';
import '../app_state/onboarding_controller.dart';
import '../features/chat/chat_screen.dart';
import '../features/chat/chat_detail_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/payment/payment_screen.dart';
import '../features/moki/moki_screen.dart';
import '../features/onboarding/onboarding_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/shell/app_shell.dart';

GoRouter buildRouter({
  required OnboardingController onboarding,
  required LocaleController locale,
}) {
  return GoRouter(
    initialLocation: '/onboarding',
    refreshListenable: onboarding,
    redirect: (context, state) {
      final onOnboarding = state.matchedLocation == '/onboarding';
      if (!onboarding.seen && !onOnboarding) return '/onboarding';
      if (onboarding.seen && onOnboarding) return '/chat';
      return null;
    },
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (ctx, state) => OnboardingScreen(controller: onboarding),
      ),
      StatefulShellRoute.indexedStack(
        builder: (ctx, state, shell) => AppShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/chat',
              builder: (ctx, state) => const ChatScreen(),
              routes: [
                GoRoute(
                  path: ':id',
                  builder: (ctx, state) {
                    final chat = state.extra as Map<String, dynamic>? ?? {};
                    return ChatDetailScreen(chat: chat);
                  },
                ),
              ],
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/moki', builder: (ctx, state) => const MokiScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/dashboard',
              builder: (ctx, state) => const DashboardScreen(),
              routes: [
                GoRoute(
                  path: 'payment',
                  builder: (ctx, state) => const PaymentScreen(),
                ),
              ],
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/profile',
              builder: (ctx, state) => const ProfileScreen(),
            ),
          ]),
        ],
      ),
    ],
  );
}
