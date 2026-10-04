// Real glassmorphic surface (`DEC-189`, product rebuild Block A).
//
// No package is used for this, deliberately: Flutter's own
// `BackdropFilter` + `ImageFilter.blur` is the real mechanism every
// glassmorphism package wraps anyway, and the whole effect is about
// forty lines. Adding a dependency for it would be a real cost (this
// repository already carries two version pins forced by Android
// toolchain breakage from third-party packages) for no capability.
//
// REAL PERFORMANCE NOTE, and the reason [GlassPanel] has a
// `blurEnabled` escape hatch: `BackdropFilter` is genuinely expensive
// on Android. Each one forces the compositor to save the layer behind
// it, blur it, and composite the result, and the cost scales with the
// blurred AREA, not with how much is drawn on top. A screen that
// stacks many of them -- a long scrolling list where every row is a
// glass card -- can drop real frames on a mid-range device. The
// pattern this app follows: glass for a small number of large,
// deliberate surfaces (a header, a sheet, a hero card), and the plain
// [solidPanelDecoration] for list rows, which looks nearly identical
// at list-row scale because there is very little behind a row for a
// blur to reveal.

import 'dart:ui';

import 'package:flutter/material.dart';

import 'quorum_dark_theme.dart';

/// A real frosted-glass panel: a blurred view of whatever is behind it,
/// a low-alpha fill, a hairline edge, and an optional accent glow.
///
/// [accent] tints both the edge and the outer glow. Passing an agent's
/// own color makes the panel read as belonging to that agent without
/// needing a label -- though per this project's accessibility rule the
/// caller is still expected to render a real icon or name as well,
/// never relying on the tint alone to say whose panel it is.
class GlassPanel extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final double radius;
  final Color? accent;

  /// How strongly [accent] tints the edge and glow. 0 disables the glow
  /// entirely while keeping the hairline neutral.
  final double accentStrength;

  /// Set false to skip the `BackdropFilter` and render a solid panel of
  /// the same dimensions and color. Used where many panels appear at
  /// once -- see this file's performance note.
  final bool blurEnabled;

  final VoidCallback? onTap;

  const GlassPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.radius = QuorumRadius.md,
    this.accent,
    this.accentStrength = 1.0,
    this.blurEnabled = true,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final borderRadius = BorderRadius.circular(radius);
    final tint = accent;
    final hasGlow = tint != null && accentStrength > 0;

    Widget surface = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        color: QuorumDarkGround.glassFill,
        border: Border.all(
          color: hasGlow
              ? Color.lerp(QuorumDarkGround.hairline, tint.withValues(alpha: 0.55), accentStrength)!
              : QuorumDarkGround.hairline,
          width: 1,
        ),
      ),
      child: Padding(padding: padding, child: child),
    );

    if (blurEnabled) {
      surface = BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: surface,
      );
    }

    // ClipRRect is required, not cosmetic: without it the BackdropFilter
    // blurs a full rectangle and the rounded corners show a hard square
    // edge of blurred content outside the border.
    Widget panel = ClipRRect(borderRadius: borderRadius, child: surface);

    if (hasGlow) {
      panel = DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: borderRadius,
          boxShadow: [
            BoxShadow(
              color: tint.withValues(alpha: 0.18 * accentStrength),
              blurRadius: 28,
              spreadRadius: -4,
            ),
          ],
        ),
        child: panel,
      );
    }

    if (onTap != null) {
      // The Material/InkWell pair sits INSIDE the clip so the ripple is
      // clipped to the rounded corners too, and is transparent so it
      // does not paint over the glass fill.
      panel = Stack(
        children: [
          panel,
          Positioned.fill(
            child: Material(
              color: Colors.transparent,
              borderRadius: borderRadius,
              child: InkWell(borderRadius: borderRadius, onTap: onTap),
            ),
          ),
        ],
      );
    }

    return panel;
  }
}

/// The cheap, non-blurred counterpart to [GlassPanel], for list rows and
/// anywhere else a real blur would cost frames for no visible gain.
/// Same visual language -- raised ground, hairline edge, optional accent
/// tint -- without the compositor cost.
BoxDecoration solidPanelDecoration({
  Color? accent,
  double radius = QuorumRadius.md,
  bool filled = true,
}) {
  return BoxDecoration(
    borderRadius: BorderRadius.circular(radius),
    color: filled ? QuorumDarkGround.surface : null,
    border: Border.all(
      color: accent != null
          ? accent.withValues(alpha: 0.35)
          : QuorumDarkGround.hairline,
      width: 1,
    ),
  );
}

/// The app's ambient background: the flat near-black base with two
/// very soft, far-apart accent blooms.
///
/// Deliberately subtle. The blooms exist so large empty areas are not
/// a dead flat field, and so the glass panels have something behind
/// them worth blurring -- a `BackdropFilter` over a perfectly uniform
/// color produces that same uniform color and the glass effect is
/// invisible. They are low enough in alpha that they never compete
/// with real content or shift the apparent color of text sitting on
/// top of them.
class QuorumAmbientBackground extends StatelessWidget {
  final Widget child;

  /// Tints the upper bloom. Pass the current agent's accent to make a
  /// whole screen feel like it belongs to that agent.
  final Color? accent;

  const QuorumAmbientBackground({super.key, required this.child, this.accent});

  @override
  Widget build(BuildContext context) {
    final top = accent ?? const Color(0xFF22D3EE);
    return DecoratedBox(
      decoration: const BoxDecoration(color: QuorumDarkGround.base),
      child: Stack(
        children: [
          Positioned(
            top: -140,
            right: -100,
            child: _Bloom(color: top, size: 340),
          ),
          const Positioned(
            bottom: -180,
            left: -120,
            child: _Bloom(color: Color(0xFFA77BFF), size: 380),
          ),
          Positioned.fill(child: child),
        ],
      ),
    );
  }
}

class _Bloom extends StatelessWidget {
  final Color color;
  final double size;

  const _Bloom({required this.color, required this.size});

  @override
  Widget build(BuildContext context) {
    // IgnorePointer so a decorative bloom can never intercept a real
    // tap intended for content above it.
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [color.withValues(alpha: 0.13), color.withValues(alpha: 0.0)],
          ),
        ),
      ),
    );
  }
}
