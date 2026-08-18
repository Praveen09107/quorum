// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// DELIBERATE, DISCLOSED ABSENCE: no test here asserts a value at exactly
// an x.5 boundary (30.5, 29.5, 27.5, etc.) — Python's round() and Dart's
// num.round() disagree exactly there (banker's rounding vs. round-half-
// away-from-zero), and this project's discipline is to wait for a real
// Dart compiler to confirm that behavior rather than guess at a disputed
// answer. Every case below was hand-verified in Python first and
// confirmed genuinely non-ambiguous under either rounding convention.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';

void main() {
  group('formatCurrency -- whole rupees, zero decimal places', () {
    test('a whole-number amount formats cleanly', () {
      expect(formatCurrency(649.0), '₹649');
    });

    test('a non-ambiguous fractional amount (30.2, both languages agree it rounds to 30)', () {
      expect(formatCurrency(30.2), '₹30');
    });
  });

  group('formatInterval', () {
    test('a non-ambiguous fractional interval (30.2 -> ~30 days)', () {
      expect(formatInterval(30.2), '~30 days');
    });

    test('a non-ambiguous fractional interval (29.6 -> ~30 days)', () {
      expect(formatInterval(29.6), '~30 days');
    });
  });

  group('sortByAmountDesc', () {
    test('ranks the most expensive subscription first', () {
      final cheap = DetectedSubscriptionData(payee: 'Spotify', averageAmount: 119.0, occurrences: 4, averageIntervalDays: 30.2);
      final expensive = DetectedSubscriptionData(payee: 'Netflix', averageAmount: 649.0, occurrences: 4, averageIntervalDays: 30.2);

      final result = sortByAmountDesc([cheap, expensive]);

      expect(result.map((s) => s.payee).toList(), ['Netflix', 'Spotify']);
    });

    test('does not mutate the input list', () {
      final a = DetectedSubscriptionData(payee: 'A', averageAmount: 100.0, occurrences: 3, averageIntervalDays: 30.2);
      final b = DetectedSubscriptionData(payee: 'B', averageAmount: 200.0, occurrences: 3, averageIntervalDays: 30.2);
      final original = [a, b];

      final result = sortByAmountDesc(original);

      expect(original.map((s) => s.payee).toList(), ['A', 'B'], reason: 'original order must survive untouched');
      expect(result.map((s) => s.payee).toList(), ['B', 'A']);
    });

    test('an empty list sorts to an empty list, not a crash', () {
      expect(sortByAmountDesc(const []), isEmpty);
    });
  });
}
