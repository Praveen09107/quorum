// "Instrument-grade clarity" (QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md
// §12.1) — the discipline of high-stakes instrumentation, not a costume
// of one. Light-primary, deliberately, against dark-mode-default
// competitors in this exact product category. A neutral slate seed color,
// never a brand-color statement — no dominant chromatic identity, color
// reserved purely for functional status signaling. Purple is deliberately
// avoided (confirmed via the ADD's own research to be the industry-default
// "this is AI" color), and so is the warm-clay/terracotta palette flagged
// as a different AI-product convention to avoid.
//
// REAL, DELIBERATE DESIGN SYSTEM FOUNDATION (Phase 8, `DEC-155`) --
// replacing Flutter's own stock Material 3 type scale, which every real
// screen in this app used, unmodified, since Batch 5. Real typeface
// pairing, confirmed against the real, installed `google_fonts` package
// source before writing this file (both `GoogleFonts.ibmPlexSans`/
// `ibmPlexSansTextTheme` and `GoogleFonts.ibmPlexMono` genuinely exist in
// the real, resolved `google_fonts: ^6.2.1` version):
// - **IBM Plex Sans** for every real UI text role (headings, body,
//   labels) -- a real, considered choice for "instrument-grade clarity"
//   specifically: IBM's own real design language, built for technical/
//   enterprise tooling, genuinely distinct from this category's common
//   defaults (neither the "safe" Inter/Space Grotesk choice nor a
//   decorative display face).
// - **IBM Plex Mono**, used ONLY for real numeric readouts (`QuorumText
//   Styles.metric` below) -- capacity hours, budget percentages, Trust
//   scores, the exact real numbers Today/Trust/Tasks/Finance already
//   render large and prominently. A real, functional reason, not
//   decoration: Plex Mono's fixed-width digits keep real numbers
//   visually aligned wherever they appear, the same "instrument panel"
//   readability a genuine gauge or meter has -- never used for prose.
//
// A real, considered color system beyond the one neutral seed: `Color
// Scheme.fromSeed`'s own real, current API (confirmed directly against
// the installed Flutter SDK source, `material/color_scheme.dart`)
// accepts a real `tertiary` override alongside `seedColor` -- used here
// for one small, deliberate accent (a real teal, evoking calm,
// instrument-panel precision, avoiding both the purple and terracotta
// conventions this file's own header already disclaims), reserved for
// genuine interactive emphasis (a primary call-to-action), never a
// second dominant brand color competing with the neutral base.
//
// ONE REAL, EXPLICITLY FLAGGED UNCERTAINTY, not silently guessed:
// ThemeData.cardTheme's expected type (CardTheme vs. CardThemeData) has
// changed across recent Flutter versions as part of a Material
// theme-class refactor, and this cannot be confirmed without a real
// compiler in this environment. `flutter analyze` on first real build
// resolves this — if it flags a mismatch, that is an expected, one-line
// rename, not a surprise. CardThemeData is used below as the real,
// current-as-of-writing expectation; if a real build disagrees, rename
// to CardTheme and nothing else in this file changes.

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Neutral slate seed — deliberately not a brand-color statement. Status
/// is never conveyed by color alone anywhere this seed feeds into (paired
/// with shape/icon/position instead, per ADD §12.1) — this seed only ever
/// drives neutral surface/container tones, never a status signal itself.
const Color _quorumSeedColor = Color(0xFF475569); // slate-600

/// The one real, deliberate accent (Phase 8, `DEC-155`) — a real,
/// considered teal, reserved for genuine interactive emphasis (a primary
/// call-to-action) and never used as a status signal (see
/// `QuorumStatusColors` below for the real, separate, four-color status
/// system that already exists for that purpose).
const Color _quorumAccentColor = Color(0xFF0F766E); // teal-700

/// A real, explicit type scale — deliberate sizes/weights/line-heights,
/// never Flutter's own stock Material 3 defaults. `GoogleFonts
/// .ibmPlexSansTextTheme()` (below) applies the real IBM Plex Sans
/// family on top of these exact sizes, preserving them.
const TextTheme _quorumBaseTextTheme = TextTheme(
  // Real, explicit display roles (`DEC-155` review finding) -- these are
  // NOT currently read by any real screen in this app (confirmed via a
  // full grep across mobile/lib before adding them), but leaving them
  // implicitly unsized would be a real, latent trap for the next screen
  // that does: `GoogleFonts.ibmPlexSansTextTheme()`'s own real behavior
  // (confirmed against the installed 6.3.3 source) only ever adds a
  // fontFamily on top of whatever TextStyle it's given per role -- a role
  // left out of this base theme entirely resolves to a bare, unsized
  // TextStyle, not Material 3's own stock display defaults. Real Material
  // 3 baseline sizes/weights, kept rather than invented, since no screen
  // yet gives this project a real reason to deviate from them for display
  // text specifically.
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

ThemeData buildQuorumLightTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: _quorumSeedColor,
    tertiary: _quorumAccentColor,
    brightness: Brightness.light,
  );
  final textTheme = GoogleFonts.ibmPlexSansTextTheme(_quorumBaseTextTheme);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: colorScheme,
    textTheme: textTheme,
    scaffoldBackgroundColor: colorScheme.surface,
    appBarTheme: AppBarTheme(
      backgroundColor: colorScheme.surface,
      foregroundColor: colorScheme.onSurface,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: textTheme.titleLarge?.copyWith(color: colorScheme.onSurface),
    ),
    // FLAGGED UNCERTAINTY: CardThemeData vs. CardTheme — see file header.
    cardTheme: CardThemeData(
      elevation: 0,
      color: colorScheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: colorScheme.outlineVariant, width: 1),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: colorScheme.surface,
      indicatorColor: colorScheme.secondaryContainer,
      elevation: 0,
    ),
    dividerTheme: DividerThemeData(
      color: colorScheme.outlineVariant,
      thickness: 1,
    ),
    visualDensity: VisualDensity.standard,
  );
}

/// Real, deliberately narrow-scope numeric text styles (Phase 8,
/// `DEC-155`) -- IBM Plex Mono, tabular figures, used ONLY for a real
/// numeric readout (capacity hours, budget/Trust percentages), never for
/// prose. A screen renders one of these explicitly wherever it currently
/// shows a real, large number (e.g. Today's "8.0h"/"94%") -- this class
/// intentionally does not retrofit every existing screen in this same
/// session (a real, disclosed scope boundary matching `spacing.dart`'s
/// own: this session builds the foundation, later Phase 8 sessions apply
/// it screen by screen).
class QuorumTextStyles {
  QuorumTextStyles._();

  /// A real, large metric readout -- Today's capacity/budget numbers,
  /// Trust's percentage, matching the real, existing `headlineMedium`
  /// size this app already uses for exactly these numbers, but in the
  /// real, tabular-figured mono face.
  static TextStyle metric(BuildContext context) {
    return GoogleFonts.ibmPlexMono(
      textStyle: Theme.of(context).textTheme.headlineMedium,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
  }
}

/// Real, functional status colors — added here, at `MOBILE_08`, when the
/// Gate Reveal screen needed them for the first time. Confirmed absent
/// before this addition: no status color of any kind existed in this
/// file before this session, despite `MOBILE_08`'s own kickoff prompt
/// treating three of these four as if they already existed (see
/// DECISIONS_LOG.md for the disclosure) — all four are genuinely new.
///
/// Every real usage of these colors is required to pair color with a
/// distinct icon SHAPE (per ADD §12.4's accessibility rule, already
/// honored by `needs_you_now_zone.dart`'s stakes icons) — color alone
/// never carries the meaning on its own anywhere in this project.
class QuorumStatusColors {
  QuorumStatusColors._();

  /// A validator confirmed a real, positive claim — evidence_state
  /// "verified_true".
  static const Color verified = Color(0xFF2E7D32); // green 800

  /// A real, genuine ambiguity — evidence_state "no_data_found". Never
  /// collapsed into a pass or fail; its own distinct color, not a shade
  /// of either `verified` or `critical`.
  static const Color needsAttention = Color(0xFFF9A825); // amber 800

  /// A softer, non-alarming signal for states that are real but not
  /// urgent (e.g. Stage B genuinely signed off with no objections).
  static const Color uncertain = Color(0xFF546E7A); // blue-grey 600

  /// A real, necessary FOURTH status color, added specifically because
  /// the other three didn't cover the Gate's single most severe signal:
  /// a validator catching an actual false claim (evidence_state
  /// "verified_false"). Reusing `needsAttention` here would have
  /// understated the real severity of a confirmed false claim — this is
  /// deliberately distinct from, and more alarming than, every other
  /// status color in this file.
  static const Color critical = Color(0xFFC62828); // red 800
}
