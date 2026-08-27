// Real tests for features/predictive_risk/predictive_risk_logic.dart.
// Zero Flutter dependencies -- plain Dart, `dart test` is the real
// verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';

RiskAssessmentData _risk({
  int matchingHistoricalWeeks = 1,
  double? pooledCorrectionRate = 0.6,
  bool isAtRisk = true,
}) {
  return RiskAssessmentData(
    weekStart: DateTime(2026, 9, 1),
    deadlineDensity: 3,
    matchingHistoricalWeeks: matchingHistoricalWeeks,
    pooledCorrectionRate: pooledCorrectionRate,
    isAtRisk: isAtRisk,
  );
}

void main() {
  group('riskMessage -- the real, honest three-state message', () {
    test('genuinely no matching real history yet is an honest "not enough" message, never a false reassurance or alarm', () {
      final message = riskMessage(_risk(matchingHistoricalWeeks: 0, pooledCorrectionRate: null, isAtRisk: false));
      expect(message, 'Not enough real history yet to predict next week.');
    });

    test('a real, flagged risk states the real, rounded percentage', () {
      final message = riskMessage(_risk(pooledCorrectionRate: 0.6, isAtRisk: true));
      expect(message, contains('60%'));
      expect(message, contains('Next week may be tight'));
    });

    test('a real, non-risky assessment with real matching history says manageable', () {
      final message = riskMessage(_risk(pooledCorrectionRate: 0.2, isAtRisk: false));
      expect(message, 'Next week looks manageable based on your real history.');
    });

    test('never conflates "no data" with "found manageable" -- both have distinct real messages', () {
      final noData = riskMessage(_risk(matchingHistoricalWeeks: 0, pooledCorrectionRate: null, isAtRisk: false));
      final manageable = riskMessage(_risk(pooledCorrectionRate: 0.1, isAtRisk: false));
      expect(noData, isNot(equals(manageable)));
    });
  });
}
