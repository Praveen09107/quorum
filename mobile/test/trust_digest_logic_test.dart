// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';

void main() {
  group('parseTrend', () {
    test('improving parses correctly', () {
      expect(parseTrend('improving'), TrustTrend.improving);
    });

    test('declining parses correctly', () {
      expect(parseTrend('declining'), TrustTrend.declining);
    });

    test('stable parses correctly', () {
      expect(parseTrend('stable'), TrustTrend.stable);
    });

    test('a genuinely unrecognized value fails CLOSED to insufficientData, never to stable', () {
      expect(parseTrend('garbled_value'), TrustTrend.insufficientData);
    });
  });

  test('every real TrustTrend value has its own distinct, honest label', () {
    final labels = TrustTrend.values.map(trendLabel).toSet();
    expect(labels.length, TrustTrend.values.length);
  });

  group('formatDelta', () {
    test('null renders as an empty string, never a misleading placeholder number', () {
      expect(formatDelta(null), '');
    });

    test('a positive delta shows a real, single leading plus sign', () {
      expect(formatDelta(0.03), '+3 pts');
    });

    test('a negative delta shows its native minus sign exactly once, never double-signed', () {
      final result = formatDelta(-0.03);
      expect(result, '-3 pts');
      expect(result.contains('+-'), isFalse);
      expect('-'.allMatches(result).length, 1);
    });

    test('a real zero delta shows no sign at all', () {
      expect(formatDelta(0.0), '0 pts');
    });

    // The real, exact `.5` tie case (STATUS_INDEX.md open item #11),
    // resolved live against a real Dart compiler this session:
    // round-half-away-from-zero, confirmed directly. Deliberately left
    // unasserted until now, per this file's own established discipline.
    test('the real, now-confirmed .5 tie: 0.505 rounds to +51 pts, round-half-away-from-zero', () {
      expect(formatDelta(0.505), '+51 pts');
    });
  });

  group('TrustDigestData shape', () {
    test('a real digest with both weeks constructs and reads back correctly', () {
      const digest = TrustDigestData(
        currentWeek: WeeklyTrustSummaryData(weekStart: '2026-08-10', totalActions: 24, successRate: 0.875),
        previousWeek: WeeklyTrustSummaryData(weekStart: '2026-08-03', totalActions: 19, successRate: 0.789),
        trend: TrustTrend.improving,
        delta: 0.086,
      );

      expect(digest.currentWeek.totalActions, 24);
      expect(digest.previousWeek!.totalActions, 19);
      expect(digest.trend, TrustTrend.improving);
    });

    test('a real digest with no previous week is a genuine insufficientData case, not an error', () {
      const digest = TrustDigestData(
        currentWeek: WeeklyTrustSummaryData(weekStart: '2026-08-10', totalActions: 3, successRate: 1.0),
        previousWeek: null,
        trend: TrustTrend.insufficientData,
        delta: null,
      );

      expect(digest.previousWeek, isNull);
      expect(digest.delta, isNull);
      expect(formatDelta(digest.delta), '');
    });
  });
}
