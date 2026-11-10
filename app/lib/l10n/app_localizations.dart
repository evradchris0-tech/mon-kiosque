import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_fr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppL10n
/// returned by `AppL10n.of(context)`.
///
/// Applications need to include `AppL10n.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppL10n.localizationsDelegates,
///   supportedLocales: AppL10n.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppL10n.supportedLocales
/// property.
abstract class AppL10n {
  AppL10n(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppL10n? of(BuildContext context) {
    return Localizations.of<AppL10n>(context, AppL10n);
  }

  static const LocalizationsDelegate<AppL10n> delegate = _AppL10nDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('fr'),
  ];

  /// No description provided for @appName.
  ///
  /// In fr, this message translates to:
  /// **'Mon Kiosque'**
  String get appName;

  /// No description provided for @appTagline.
  ///
  /// In fr, this message translates to:
  /// **'Le 3-en-1 de la PME camerounaise'**
  String get appTagline;

  /// No description provided for @poweredByMoki.
  ///
  /// In fr, this message translates to:
  /// **'Propulsé par Moki'**
  String get poweredByMoki;

  /// No description provided for @onboardingStartCta.
  ///
  /// In fr, this message translates to:
  /// **'Commencer'**
  String get onboardingStartCta;

  /// No description provided for @onboardingNextCta.
  ///
  /// In fr, this message translates to:
  /// **'Suivant'**
  String get onboardingNextCta;

  /// No description provided for @onboardingSkipCta.
  ///
  /// In fr, this message translates to:
  /// **'Passer'**
  String get onboardingSkipCta;

  /// No description provided for @onboardingTitle1.
  ///
  /// In fr, this message translates to:
  /// **'Encaisse, sans te prendre la tête'**
  String get onboardingTitle1;

  /// No description provided for @onboardingBody1.
  ///
  /// In fr, this message translates to:
  /// **'Cash, Orange Money, ou les deux en même temps. Moki enregistre tout automatiquement.'**
  String get onboardingBody1;

  /// No description provided for @onboardingTitle2.
  ///
  /// In fr, this message translates to:
  /// **'Moki travaille pour toi 24/7'**
  String get onboardingTitle2;

  /// No description provided for @onboardingBody2.
  ///
  /// In fr, this message translates to:
  /// **'Ton assistant en Camfranglais : factures, relances clients, rapports du soir. Toi, tu valides.'**
  String get onboardingBody2;

  /// No description provided for @onboardingTitle3.
  ///
  /// In fr, this message translates to:
  /// **'Vois clair sur ton business'**
  String get onboardingTitle3;

  /// No description provided for @onboardingBody3.
  ///
  /// In fr, this message translates to:
  /// **'Ton chiffre d\'affaires, tes top clients, tes impayés — en temps réel. Crédit dès le 6e mois.'**
  String get onboardingBody3;

  /// No description provided for @tabChat.
  ///
  /// In fr, this message translates to:
  /// **'Chat'**
  String get tabChat;

  /// No description provided for @tabMoki.
  ///
  /// In fr, this message translates to:
  /// **'Moki'**
  String get tabMoki;

  /// No description provided for @tabDashboard.
  ///
  /// In fr, this message translates to:
  /// **'Tableau'**
  String get tabDashboard;

  /// No description provided for @tabProfile.
  ///
  /// In fr, this message translates to:
  /// **'Profil'**
  String get tabProfile;

  /// No description provided for @chatEmptyTitle.
  ///
  /// In fr, this message translates to:
  /// **'Tes conversations WhatsApp'**
  String get chatEmptyTitle;

  /// No description provided for @chatEmptyBody.
  ///
  /// In fr, this message translates to:
  /// **'Branche ton WhatsApp Business pour que Moki t\'aide à répondre et à relancer.'**
  String get chatEmptyBody;

  /// No description provided for @mokiEmptyTitle.
  ///
  /// In fr, this message translates to:
  /// **'Salut, moi c\'est Moki 👋'**
  String get mokiEmptyTitle;

  /// No description provided for @mokiEmptyBody.
  ///
  /// In fr, this message translates to:
  /// **'Demande-moi de faire une facture, de relancer un client, ou de regarder tes ventes.'**
  String get mokiEmptyBody;

  /// No description provided for @mokiSuggestionInvoice.
  ///
  /// In fr, this message translates to:
  /// **'Fais-moi une facture'**
  String get mokiSuggestionInvoice;

  /// No description provided for @mokiSuggestionRelance.
  ///
  /// In fr, this message translates to:
  /// **'Relance Mme Biya'**
  String get mokiSuggestionRelance;

  /// No description provided for @mokiSuggestionReport.
  ///
  /// In fr, this message translates to:
  /// **'Comment était hier ?'**
  String get mokiSuggestionReport;

  /// No description provided for @dashboardTodayRevenue.
  ///
  /// In fr, this message translates to:
  /// **'Chiffre d\'affaires du jour'**
  String get dashboardTodayRevenue;

  /// No description provided for @dashboardDigitalRate.
  ///
  /// In fr, this message translates to:
  /// **'Taux de digitalisation'**
  String get dashboardDigitalRate;

  /// No description provided for @dashboardTopClients.
  ///
  /// In fr, this message translates to:
  /// **'Top clients'**
  String get dashboardTopClients;

  /// No description provided for @dashboardUnpaid.
  ///
  /// In fr, this message translates to:
  /// **'Impayés'**
  String get dashboardUnpaid;

  /// No description provided for @dashboardCreditScore.
  ///
  /// In fr, this message translates to:
  /// **'Score crédit'**
  String get dashboardCreditScore;

  /// No description provided for @profileLanguage.
  ///
  /// In fr, this message translates to:
  /// **'Langue'**
  String get profileLanguage;

  /// No description provided for @profileSubscription.
  ///
  /// In fr, this message translates to:
  /// **'Abonnement'**
  String get profileSubscription;

  /// No description provided for @profileSecurity.
  ///
  /// In fr, this message translates to:
  /// **'Sécurité'**
  String get profileSecurity;

  /// No description provided for @profileSupport.
  ///
  /// In fr, this message translates to:
  /// **'Support'**
  String get profileSupport;

  /// No description provided for @profileAbout.
  ///
  /// In fr, this message translates to:
  /// **'À propos'**
  String get profileAbout;

  /// No description provided for @profileSignOut.
  ///
  /// In fr, this message translates to:
  /// **'Se déconnecter'**
  String get profileSignOut;

  /// No description provided for @languageFrench.
  ///
  /// In fr, this message translates to:
  /// **'Français'**
  String get languageFrench;

  /// No description provided for @languageEnglish.
  ///
  /// In fr, this message translates to:
  /// **'Anglais'**
  String get languageEnglish;

  /// No description provided for @planStarter.
  ///
  /// In fr, this message translates to:
  /// **'Starter'**
  String get planStarter;

  /// No description provided for @planPlus.
  ///
  /// In fr, this message translates to:
  /// **'Plus'**
  String get planPlus;

  /// No description provided for @planPro.
  ///
  /// In fr, this message translates to:
  /// **'Pro'**
  String get planPro;

  /// No description provided for @planEmpire.
  ///
  /// In fr, this message translates to:
  /// **'Empire'**
  String get planEmpire;
}

class _AppL10nDelegate extends LocalizationsDelegate<AppL10n> {
  const _AppL10nDelegate();

  @override
  Future<AppL10n> load(Locale locale) {
    return SynchronousFuture<AppL10n>(lookupAppL10n(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'fr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppL10nDelegate old) => false;
}

AppL10n lookupAppL10n(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppL10nEn();
    case 'fr':
      return AppL10nFr();
  }

  throw FlutterError(
    'AppL10n.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
