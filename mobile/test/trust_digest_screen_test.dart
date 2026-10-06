// Real widget tests for features/trust_digest/trust_digest_screen.dart --
// the redesign's own new real two-bar trend comparison.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_screen.dart';

Widget _harness(TrustDigestData digest) {
  return MaterialApp(home: Scaffold(body: TrustDigestScreen(digest: digest)));
}

void main() {
  testWidgets('a real digest with both weeks shows the real two-bar comparison with both real percentages', (tester) async {
    await tester.pumpWidget(_harness(const TrustDigestData(
      currentWeek: WeeklyTrustSummaryData(weekStart: '2026-09-28', totalActions: 10, successRate: 0.9),
      previousWeek: WeeklyTrustSummaryData(weekStart: '2026-09-21', totalActions: 8, successRate: 0.75),
      trend: TrustTrend.improving,
      delta: 0.15,
    )));

    expect(find.text('90%'), findsOneWidget);
    expect(find.text('75%'), findsOneWidget);
    expect(find.text('This week'), findsWidgets);
    expect(find.text('Last week'), findsWidgets);
  });

  testWidgets('a real digest with no previous week shows no comparison bars -- never a fabricated single bar standing in for insufficient data', (tester) async {
    await tester.pumpWidget(_harness(const TrustDigestData(
      currentWeek: WeeklyTrustSummaryData(weekStart: '2026-09-28', totalActions: 3, successRate: 1.0),
      previousWeek: null,
      trend: TrustTrend.insufficientData,
      delta: null,
    )));

    // The real percentage text still appears once, inside the real
    // `_WeekRow`'s own subtitle -- but no second, fabricated "100%" bar
    // for a comparison that was never actually computed.
    expect(find.textContaining('100%'), findsOneWidget);
    expect(find.text('Last week'), findsNothing);
  });
}
