// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// HONEST DISCLOSURE: this session's real spec describes 14 total tests
// across both languages (2 Python + 12 Dart). Since
// `backend/features/self_test_harness.py` does not exist in this
// repository (see the file under test's own header comment), there is
// no real Python file to add the 2 backend tests to this session. The
// 12 real Dart tests below are the full, real mobile-side coverage.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/trust/trust_logic.dart';

void main() {
  group('parseTarget -- the real, most important honesty check', () {
    test('real_gate parses to SelfTestTarget.realGate', () {
      expect(parseTarget('real_gate'), SelfTestTarget.realGate);
    });

    test('stub parses to SelfTestTarget.stub', () {
      expect(parseTarget('stub'), SelfTestTarget.stub);
    });

    test('a genuinely unrecognized value fails CLOSED to stub, never silently claims realGate', () {
      expect(parseTarget('garbled_unexpected_value'), SelfTestTarget.stub);
    });
  });

  group('targetLabel', () {
    test('stub gets an honest, unmistakable label', () {
      expect(targetLabel(SelfTestTarget.stub), 'Testing against a demo Gate, not the real one yet');
    });

    test('realGate gets its own distinct, honest label', () {
      expect(targetLabel(SelfTestTarget.realGate), 'Testing against the real Gate');
    });

    test('the two labels are provably distinct -- the stub-vs-real distinction is impossible to miss', () {
      expect(targetLabel(SelfTestTarget.stub), isNot(targetLabel(SelfTestTarget.realGate)));
    });
  });

  group('formatCatchRate', () {
    test('the real, hand-verified §5.14 example: 11 of 12 caught rounds to 92%', () {
      expect(formatCatchRate(11, 12), '92%');
    });

    test('zero total is genuinely "No data yet", not a division-by-zero crash or "0%"', () {
      expect(formatCatchRate(0, 0), 'No data yet');
    });

    test('zero caught out of a real nonzero total is a real, distinct "0%"', () {
      expect(formatCatchRate(0, 10), '0%');
      expect(formatCatchRate(0, 10), isNot(formatCatchRate(0, 0)));
    });
  });

  group('TrustData / ScenarioResultData shape', () {
    test('a real result with a missed scenario constructs and reads back correctly', () {
      const trust = TrustData(
        total: 12,
        caught: 11,
        missed: [ScenarioResultData(scenarioId: 'S7', expected: 'reject', actual: 'approve', passed: false)],
        results: [],
        target: SelfTestTarget.stub,
      );

      expect(trust.missed.length, 1);
      expect(trust.missed.first.passed, isFalse);
    });

    test('a real result with everything caught has a genuinely empty missed list', () {
      const trust = TrustData(total: 12, caught: 12, missed: [], results: [], target: SelfTestTarget.stub);
      expect(trust.missed, isEmpty);
    });

    test('results carries every real scenario, passed and failed alike -- never pre-filtered', () {
      const trust = TrustData(
        total: 2,
        caught: 1,
        missed: [ScenarioResultData(scenarioId: 'S7', expected: 'reject', actual: 'approve', passed: false)],
        results: [
          ScenarioResultData(scenarioId: 'S1', expected: 'approve', actual: 'approve', passed: true),
          ScenarioResultData(scenarioId: 'S7', expected: 'reject', actual: 'approve', passed: false),
        ],
        target: SelfTestTarget.stub,
      );

      expect(trust.results.length, 2);
      expect(trust.results.where((r) => !r.passed).length, 1);
    });
  });
}
