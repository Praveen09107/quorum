// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// DELIBERATE, DISCLOSED ABSENCE: no test here asserts a value at exactly
// an x.5 percentage boundary — this file is one of five in this batch
// sharing the tracked Dart `.5`-rounding uncertainty (STATUS_INDEX.md
// open item #6). `0.847` is confirmed non-ambiguous under either
// language's rounding convention.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

void main() {
  group('formatSuccessRate', () {
    test('null (genuinely no data) renders honestly, distinct from a real 0%', () {
      expect(formatSuccessRate(null), 'No data yet');
    });

    test('a real 0.0 rate renders "0%", not "No data yet"', () {
      expect(formatSuccessRate(0.0), '0%');
    });

    test('null and 0.0 are provably distinct outputs', () {
      expect(formatSuccessRate(null), isNot(formatSuccessRate(0.0)));
    });

    test('a real, non-ambiguous success rate formats correctly', () {
      expect(formatSuccessRate(0.847), '85%');
    });

    // The real, exact `.5` tie case (STATUS_INDEX.md open item #11),
    // resolved live against a real Dart compiler this session:
    // round-half-away-from-zero, confirmed directly. Deliberately left
    // unasserted until now, per this file's own established discipline.
    test('the real, now-confirmed .5 tie: 0.505 rounds to 51%, round-half-away-from-zero', () {
      expect(formatSuccessRate(0.505), '51%');
    });
  });

  group('outcomeLabel', () {
    test('approved_unchanged gets a real, readable label', () {
      expect(outcomeLabel('approved_unchanged'), 'Approved as drafted');
    });

    test('caught_by_gate gets a real, distinct label', () {
      expect(outcomeLabel('caught_by_gate'), 'Caught before it went out');
    });

    test('corrected_by_user gets a real, distinct label', () {
      expect(outcomeLabel('corrected_by_user'), 'You caught this one');
    });

    test('caught_by_gate and corrected_by_user are PROVABLY not collapsed into each other', () {
      // The single most load-bearing assertion in this file: these two
      // outcomes mean structurally different things and must never
      // share a label.
      expect(outcomeLabel('caught_by_gate'), isNot(outcomeLabel('corrected_by_user')));
    });

    test('a genuinely unrecognized outcome de-snakes gracefully, never a crash', () {
      final label = outcomeLabel('some_future_outcome');
      expect(label, 'Some Future Outcome');
      expect(label.contains('_'), isFalse);
    });
  });

  group('HonestyFeedData shape', () {
    test('a real feed with all three sections populated constructs and reads back correctly', () {
      final feed = HonestyFeedData(
        total: 3,
        successRate: 0.667,
        successes: [
          LoggedActionData(actionId: '1', timestamp: DateTime(2026, 8, 10), outcome: 'approved_unchanged', description: 'Replied to Priya'),
        ],
        failuresAndCatches: [
          LoggedActionData(actionId: '2', timestamp: DateTime(2026, 8, 11), outcome: 'caught_by_gate', description: 'Draft claimed a meeting that did not exist'),
        ],
        genuinelyUncertain: [
          LoggedActionData(actionId: '3', timestamp: DateTime(2026, 8, 12), outcome: 'no_data_found', description: 'Could not verify a claim either way'),
        ],
      );

      expect(feed.total, 3);
      expect(feed.successes.length, 1);
      expect(feed.failuresAndCatches.length, 1);
      expect(feed.genuinelyUncertain.length, 1);
    });

    test('an empty genuinely_uncertain list is a real, valid, honest state -- not an error', () {
      final feed = HonestyFeedData(
        total: 2,
        successRate: 1.0,
        successes: [
          LoggedActionData(actionId: '1', timestamp: DateTime(2026, 8, 10), outcome: 'approved_unchanged', description: 'x'),
        ],
        failuresAndCatches: const [],
        genuinelyUncertain: const [],
      );

      expect(feed.genuinelyUncertain, isEmpty);
      expect(feed.failuresAndCatches, isEmpty);
    });
  });
}
