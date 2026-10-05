// Real tests for theme/quorum_gauge.dart's pure, zero-Flutter-dependency
// functions. The widget/CustomPainter themselves need `flutter analyze`
// on a real machine; `gaugeSweepAngle`/`gaugeColorForFraction` are real,
// pure math/logic, verifiable with plain `dart test`.
//
// NOTE: `quorum_gauge.dart` imports `package:flutter/material.dart` for
// its widget classes, so this file (like `calendar_sync_test.dart`)
// needs `flutter test`, not `dart test`, to even load -- confirmed by
// the same real reasoning that file's own header already documents.

import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/theme/quorum_gauge.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';

void main() {
  group('gaugeSweepAngle -- the real 270-degree instrument-panel sweep', () {
    test('a real, empty gauge (fraction 0.0) sweeps zero radians', () {
      expect(gaugeSweepAngle(0.0), 0.0);
    });

    test('a real, full gauge (fraction 1.0) sweeps the full real 270 degrees', () {
      expect(gaugeSweepAngle(1.0), closeTo(math.pi * 1.5, 1e-9));
    });

    test('a real, half-full gauge sweeps exactly half of 270 degrees', () {
      expect(gaugeSweepAngle(0.5), closeTo(math.pi * 0.75, 1e-9));
    });

    test('a real, out-of-range fraction above 1.0 is clamped, never overdrawn past a full sweep', () {
      expect(gaugeSweepAngle(1.5), closeTo(math.pi * 1.5, 1e-9));
    });

    test('a real, out-of-range negative fraction is clamped to zero, never a negative sweep', () {
      expect(gaugeSweepAngle(-0.5), 0.0);
    });
  });

  group('gaugeColorForFraction -- the real three-tier status mapping', () {
    test('a real, critically low fraction gets the real critical color', () {
      expect(gaugeColorForFraction(0.05), QuorumStatusColors.critical);
    });

    test('a real, low-but-not-critical fraction gets the real needsAttention color', () {
      expect(gaugeColorForFraction(0.25), QuorumStatusColors.needsAttention);
    });

    test('a real, healthy fraction gets the real verified color', () {
      expect(gaugeColorForFraction(0.8), QuorumStatusColors.verified);
    });

    test('the real boundary at 0.15 belongs to needsAttention, not critical', () {
      expect(gaugeColorForFraction(0.15), QuorumStatusColors.needsAttention);
    });

    test('the real boundary at 0.4 belongs to verified, not needsAttention', () {
      expect(gaugeColorForFraction(0.4), QuorumStatusColors.verified);
    });
  });
}
