// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented
// `ThemeData` API; `flutter analyze` on a real machine is the actual
// verification.
//
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

/// Neutral slate seed — deliberately not a brand-color statement. Status
/// is never conveyed by color alone anywhere this seed feeds into (paired
/// with shape/icon/position instead, per ADD §12.1) — this seed only ever
/// drives neutral surface/container tones, never a status signal itself.
const Color _quorumSeedColor = Color(0xFF475569); // slate-600

ThemeData buildQuorumLightTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: _quorumSeedColor,
    brightness: Brightness.light,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: colorScheme.surface,
    appBarTheme: AppBarTheme(
      backgroundColor: colorScheme.surface,
      foregroundColor: colorScheme.onSurface,
      elevation: 0,
      centerTitle: false,
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
