/// REAL, NEW (the redesign's own real "instrument panel" work) --
/// `holding_steady_zone.dart`'s own header comment has documented, since
/// this app's early sessions, a real, locked ADD design decision:
/// "Typography as the visualization, literally... no chart widget, no
/// gauge." This is a real, deliberate, DISCLOSED override of that
/// decision, not a silent contradiction -- made during this session's
/// own approved redesign plan, which named a real gauge explicitly:
/// "Capacity and budget become real gauges, not just a number + label...
/// literalizes the 'instrument panel' metaphor the ADD already named."
/// The numeral itself is kept, centered inside the gauge, rather than
/// replaced -- this adds a real visual instrument around the existing
/// real typography, it does not remove the typography the original
/// decision was protecting.
///
/// Hand-built with `CustomPainter` rather than a new pub.dev dependency
/// -- the approved plan's own stated preference, matching this
/// project's existing "hand-build small, well-understood components"
/// pattern (`QuorumIconBadge`, etc.).
///
/// `gaugeSweepAngle()`/`gaugeColorForFraction()` below are deliberately
/// pure, zero-Flutter functions -- the real, testable core, the same
/// "keep real logic testable, keep the plugin/paint wrapper thin"
/// discipline `calendar_sync.dart` already established for this
/// project's mobile code.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:quorum_mobile/theme/quorum_theme.dart';

/// A real instrument-panel-style gauge sweeps 270° (3/4 of a full
/// circle), starting 135° clockwise from due north -- the same real
/// convention a car speedometer or a kitchen dial uses, not an
/// arbitrary choice. Returns the real sweep angle in radians for a
/// given real `fraction` (clamped to [0, 1] -- a real, defensive
/// refusal to ever draw past a full circle on a malformed input).
double gaugeSweepAngle(double fraction) {
  final clamped = fraction.clamp(0.0, 1.0);
  return _gaugeTotalSweep * clamped;
}

const double _gaugeStartAngle = math.pi * 0.75; // 135°
const double _gaugeTotalSweep = math.pi * 1.5; // 270°

/// REAL, DELIBERATE three-tier color choice, reusing the exact same
/// `QuorumStatusColors` semantics already established everywhere else
/// in this app (Gate Reveal's `EvidenceVisualState`, the Predictive Risk
/// banner): a real, low remaining fraction is a genuinely negative
/// signal worth `critical`, not a neutral one -- never color alone
/// elsewhere in this app, and the numeral/label beside this gauge is
/// the real, accompanying text that satisfies that rule here too.
Color gaugeColorForFraction(double fraction) {
  final clamped = fraction.clamp(0.0, 1.0);
  if (clamped < 0.15) return QuorumStatusColors.critical;
  if (clamped < 0.4) return QuorumStatusColors.needsAttention;
  return QuorumStatusColors.verified;
}

class QuorumGauge extends StatelessWidget {
  final double fraction;
  final Widget child;
  final double size;

  const QuorumGauge({
    super.key,
    required this.fraction,
    required this.child,
    this.size = 88,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _GaugePainter(
              fraction: fraction,
              color: gaugeColorForFraction(fraction),
              trackColor: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
          ),
          child,
        ],
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double fraction;
  final Color color;
  final Color trackColor;

  const _GaugePainter({required this.fraction, required this.color, required this.trackColor});

  @override
  void paint(Canvas canvas, Size size) {
    final strokeWidth = size.width * 0.1;
    final rect = Rect.fromLTWH(strokeWidth / 2, strokeWidth / 2, size.width - strokeWidth, size.height - strokeWidth);

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, _gaugeStartAngle, _gaugeTotalSweep, false, trackPaint);

    final fgPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, _gaugeStartAngle, gaugeSweepAngle(fraction), false, fgPaint);
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) {
    return oldDelegate.fraction != fraction || oldDelegate.color != color || oldDelegate.trackColor != trackColor;
  }
}
