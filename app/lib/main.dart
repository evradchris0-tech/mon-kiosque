import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'package:mon_kiosque/l10n/app_localizations.dart';
import 'src/app_state/locale_controller.dart';
import 'src/app_state/onboarding_controller.dart';
import 'src/app_state/simulation_controller.dart';
import 'src/data/sales_controller.dart';
import 'src/router/app_router.dart';
import 'src/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final locale = await LocaleController.load();
  final onboarding = await OnboardingController.load();
  final simulation = SimulationController();
  final sales = SalesController();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: locale),
        ChangeNotifierProvider.value(value: onboarding),
        ChangeNotifierProvider.value(value: simulation),
        ChangeNotifierProvider.value(value: sales),
      ],
      child: const MonKiosqueApp(),
    ),
  );
}

class MonKiosqueApp extends StatefulWidget {
  const MonKiosqueApp({super.key});

  @override
  State<MonKiosqueApp> createState() => _MonKiosqueAppState();
}

class _MonKiosqueAppState extends State<MonKiosqueApp> {
  late final _router = buildRouter(
    onboarding: context.read<OnboardingController>(),
    locale: context.read<LocaleController>(),
  );

  @override
  void initState() {
    super.initState();
    context.read<LocaleController>().addListener(_onChange);
  }

  @override
  void dispose() {
    // Note: Provider might dispose controllers if not using .value
    super.dispose();
  }

  void _onChange() => setState(() {});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Mon Kiosque',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      locale: context.watch<LocaleController>().locale,
      supportedLocales: const [Locale('fr'), Locale('en')],
      localizationsDelegates: const [
        AppL10n.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: _router,
    );
  }
}
