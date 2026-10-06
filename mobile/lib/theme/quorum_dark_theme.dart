// The real dark "mission control" design system (`DEC-189`, product
// rebuild Block A).
//
// A DELIBERATE, DISCLOSED SUPERSESSION, not an oversight. `theme/
// quorum_theme.dart` implements `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`
// §12.1's visual direction: light-primary, a neutral slate seed, "no
// dominant chromatic identity," purple explicitly avoided. That
// direction was real and reasoned. It is superseded here at the
// product owner's explicit, confirmed direction after using the
// shipped app, with the specific brief: dark-first, colorful,
// glassmorphic, "many visual treats."
//
// WHAT IS SUPERSEDED: the aesthetic only -- ground color, chromatic
// identity, and the restraint on accent use.
//
// WHAT IS NOT SUPERSEDED, and is carried forward verbatim because it
// is an honesty requirement rather than a style preference:
//   - Status is NEVER carried by color alone. Every status color in
//     this file is required to be rendered alongside a distinct icon
//     or shape (ADD §12.4).
//   - Failures get equal visual prominence to successes. Nothing in
//     this palette makes a caught error quieter than a pass.
//   - Three-valued evidence stays three-valued. `verified`,
//     `needsAttention` and `critical` are genuinely distinct colors,
//     never shades of one another, so `no_data_found` can never be
//     visually collapsed into a pass or a fail.
//
// `quorum_theme.dart` is deliberately left in place and untouched
// rather than deleted: it is still referenced by existing screens that
// the rebuild has not yet reached, and removing it would break them
// for no benefit. It becomes dead code only once every screen has
// migrated, and deleting it then is a real, separate cleanup.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// The real layered ground. Deliberately not pure black: a slight blue
/// bias (the channels are not equal) means the agent accents read as
/// sitting *in* the surface rather than floating on top of it, and
/// large dark areas avoid the flat, dead look pure `#000000` gives on
/// an OLED panel. Three levels, used consistently -- base behind
/// everything, surface for a panel, raised for something lifted above
/// a panel.
class QuorumDarkGround {
  QuorumDarkGround._();

  static const Color base = Color(0xFF07090D);
  static const Color surface = Color(0xFF0E1117);
  static const Color raised = Color(0xFF141922);

  /// A hairline border for a glass edge. Low-alpha white rather than a
  /// solid grey so it picks up whatever is behind it.
  static const Color hairline = Color(0x1FFFFFFF);

  /// The fill used by a glass panel over [base]. Kept low -- the blur
  /// behind it, not the fill, is what makes the material read as glass.
  static const Color glassFill = Color(0x0FFFFFFF);

  /// Primary and secondary text on a dark ground. Not pure white:
  /// full-brightness white on near-black is genuinely harsh at body
  /// sizes and causes visible halation on OLED.
  static const Color textPrimary = Color(0xFFE8ECF4);
  static const Color textSecondary = Color(0xFF99A3B5);
  static const Color textTertiary = Color(0xFF6B7585);
}

/// Real, functional status colors for the dark ground.
///
/// These are a deliberate RE-TUNE of `QuorumStatusColors` in
/// `quorum_theme.dart`, not a second, competing status vocabulary: the
/// same four meanings, the same strict three-valued discipline, with
/// luminance raised so each one stays legible against [QuorumDarkGround
/// .base]. The light-theme values (green 800, amber 800, red 800) were
/// chosen for contrast against white and genuinely fail to read on
/// near-black, so reusing them here would have quietly degraded exactly
/// the signals that matter most.
class QuorumDarkStatus {
  QuorumDarkStatus._();

  /// `evidence_state == "verified_true"`. Always paired with a check
  /// icon.
  static const Color verified = Color(0xFF3DD68C);

  /// `evidence_state == "no_data_found"` -- the real, honest third
  /// state. Its own distinct hue, never a shade of [verified] or
  /// [critical], so it can never be read as "sort of passed" or "sort
  /// of failed". Always paired with a half-filled / question icon.
  static const Color needsAttention = Color(0xFFFFB443);

  /// `evidence_state == "verified_false"` -- the Gate catching a real
  /// false claim, this system's single most severe signal. Always
  /// paired with an error icon.
  static const Color critical = Color(0xFFFF5A6E);

  /// Real but not urgent (Stage B signed off with no objections, a
  /// resolved item, an inactive state). Deliberately desaturated so it
  /// never competes with the three meaningful states above.
  static const Color neutral = Color(0xFF7A8699);
}

/// Real, explicit dark type scale. Same sizes and weights as the light
/// theme's scale -- the rebuild changes the ground and the color, not
/// the typographic rhythm, and keeping the scale identical means a
/// screen can migrate between themes without its layout shifting.
const TextTheme _darkBaseTextTheme = TextTheme(
  displayLarge: TextStyle(fontSize: 57, height: 64 / 57, fontWeight: FontWeight.w600),
  displayMedium: TextStyle(fontSize: 45, height: 52 / 45, fontWeight: FontWeight.w600),
  displaySmall: TextStyle(fontSize: 36, height: 44 / 36, fontWeight: FontWeight.w600),
  headlineLarge: TextStyle(fontSize: 32, height: 40 / 32, fontWeight: FontWeight.w600),
  headlineMedium: TextStyle(fontSize: 28, height: 36 / 28, fontWeight: FontWeight.w600),
  headlineSmall: TextStyle(fontSize: 24, height: 32 / 24, fontWeight: FontWeight.w600),
  titleLarge: TextStyle(fontSize: 22, height: 28 / 22, fontWeight: FontWeight.w600),
  titleMedium: TextStyle(fontSize: 18, height: 26 / 18, fontWeight: FontWeight.w600),
  titleSmall: TextStyle(fontSize: 16, height: 24 / 16, fontWeight: FontWeight.w500),
  bodyLarge: TextStyle(fontSize: 16, height: 24 / 16, fontWeight: FontWeight.w400),
  bodyMedium: TextStyle(fontSize: 14, height: 20 / 14, fontWeight: FontWeight.w400),
  bodySmall: TextStyle(fontSize: 12, height: 16 / 12, fontWeight: FontWeight.w400),
  labelLarge: TextStyle(fontSize: 14, height: 20 / 14, fontWeight: FontWeight.w500),
  labelMedium: TextStyle(fontSize: 12, height: 16 / 12, fontWeight: FontWeight.w500),
  labelSmall: TextStyle(fontSize: 11, height: 16 / 11, fontWeight: FontWeight.w500, letterSpacing: 0.5),
);

/// Radii, used consistently so nothing looks hand-placed.
class QuorumRadius {
  QuorumRadius._();

  static const double sm = 10.0;
  static const double md = 16.0;
  static const double lg = 22.0;
  static const double pill = 999.0;
}

ThemeData buildQuorumDarkTheme() {
  const gateAccent = Color(0xFF22D3EE);

  final colorScheme = ColorScheme.fromSeed(
    seedColor: gateAccent,
    brightness: Brightness.dark,
  ).copyWith(
    surface: QuorumDarkGround.base,
    onSurface: QuorumDarkGround.textPrimary,
    surfaceContainerLowest: QuorumDarkGround.base,
    surfaceContainerLow: QuorumDarkGround.surface,
    surfaceContainer: QuorumDarkGround.surface,
    surfaceContainerHigh: QuorumDarkGround.raised,
    surfaceContainerHighest: QuorumDarkGround.raised,
    primary: gateAccent,
    onPrimary: QuorumDarkGround.base,
    outlineVariant: QuorumDarkGround.hairline,
    error: QuorumDarkStatus.critical,
  );

  final textTheme = GoogleFonts.ibmPlexSansTextTheme(_darkBaseTextTheme).apply(
    bodyColor: QuorumDarkGround.textPrimary,
    displayColor: QuorumDarkGround.textPrimary,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: colorScheme,
    textTheme: textTheme,
    scaffoldBackgroundColor: QuorumDarkGround.base,
    canvasColor: QuorumDarkGround.base,
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      foregroundColor: QuorumDarkGround.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: textTheme.titleLarge?.copyWith(color: QuorumDarkGround.textPrimary),
      // A light status-bar icon set, so the system clock and battery
      // stay legible against this theme's near-black ground. Without
      // this they inherit the platform default and can render dark-on-
      // dark on a real device.
      systemOverlayStyle: SystemUiOverlayStyle.light,
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: QuorumDarkGround.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(QuorumRadius.md),
        side: const BorderSide(color: QuorumDarkGround.hairline, width: 1),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: QuorumDarkGround.surface,
      indicatorColor: gateAccent.withValues(alpha: 0.16),
      elevation: 0,
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => textTheme.labelMedium!.copyWith(
          color: states.contains(WidgetState.selected) ? gateAccent : QuorumDarkGround.textTertiary,
        ),
      ),
      iconTheme: WidgetStateProperty.resolveWith(
        (states) => IconThemeData(
          color: states.contains(WidgetState.selected) ? gateAccent : QuorumDarkGround.textTertiary,
        ),
      ),
    ),
    dividerTheme: const DividerThemeData(color: QuorumDarkGround.hairline, thickness: 1),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: QuorumDarkGround.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(QuorumRadius.lg)),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: QuorumDarkGround.raised,
      side: const BorderSide(color: QuorumDarkGround.hairline),
      labelStyle: textTheme.labelMedium!.copyWith(color: QuorumDarkGround.textSecondary),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(QuorumRadius.pill)),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: QuorumDarkGround.raised,
      contentTextStyle: textTheme.bodyMedium!.copyWith(color: QuorumDarkGround.textPrimary),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(QuorumRadius.sm)),
    ),
    visualDensity: VisualDensity.standard,
  );
}

/// Numeric readouts on the dark ground -- IBM Plex Mono with tabular
/// figures, the same functional reasoning `quorum_theme.dart` already
/// established (fixed-width digits keep real numbers aligned, the way a
/// genuine instrument panel does), extended here because the rebuild
/// shows far more numbers in far more places.
///
/// Used for every number, timing, ID, model name and validator label in
/// the app -- deliberately broader than the light theme's narrow "big
/// readouts only" scope. On a mission-control surface, mono type is
/// what distinguishes machine-reported fact from written prose, so the
/// distinction carries real meaning rather than being decorative.
class QuorumMono {
  QuorumMono._();

  static TextStyle _mono(TextStyle? base, Color? color) => GoogleFonts.ibmPlexMono(
        textStyle: base,
        color: color,
        fontFeatures: const [FontFeature.tabularFigures()],
      );

  /// A large, standalone readout -- a gauge's center value, a headline
  /// metric.
  static TextStyle metric(BuildContext context, {Color? color}) =>
      _mono(Theme.of(context).textTheme.headlineMedium, color ?? QuorumDarkGround.textPrimary);

  /// A numeric value inside a dense list row.
  static TextStyle metricSmall(BuildContext context, {Color? color}) =>
      _mono(Theme.of(context).textTheme.titleMedium, color ?? QuorumDarkGround.textPrimary);

  /// Machine detail at the smallest readable size -- elapsed
  /// milliseconds, a model name, a validator identifier, a trace id.
  static TextStyle detail(BuildContext context, {Color? color}) =>
      _mono(Theme.of(context).textTheme.bodySmall, color ?? QuorumDarkGround.textTertiary);

  /// An uppercase section label. Letter-spaced, because uppercase text
  /// at small sizes is genuinely harder to read without it.
  static TextStyle label(BuildContext context, {Color? color}) =>
      _mono(Theme.of(context).textTheme.labelSmall, color ?? QuorumDarkGround.textSecondary)
          .copyWith(letterSpacing: 1.0);
}
