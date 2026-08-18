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
