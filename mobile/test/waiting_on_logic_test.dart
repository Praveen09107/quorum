// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// HONEST DISCREPANCY, disclosed per this project's standing discipline:
// this session's own real spec document
// (specs/tier4_mobile/MOBILE_10_WAITING_ON.md) states 9 real tests; the
// batch guide's pasted kickoff/checklist separately says 8. Built to the
// spec's own authoritative count.
//
// The exact hand-verified date case: August 10 09:00 to August 15 14:00
// is exactly 5 real days, confirmed in Python before this file existed.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';

void main() {
  test('daysSince computes the real, hand-verified 5-day case correctly', () {
    final sentAt = DateTime(2026, 8, 10, 9, 0);
    final now = DateTime(2026, 8, 15, 14, 0);
    expect(daysSince(sentAt, now), 5);
  });

  group('formatStaleness', () {
    test('0 days is "Today"', () {
      expect(formatStaleness(0), 'Today');
    });

    test('1 day uses the real singular form, "1 day ago"', () {
      expect(formatStaleness(1), '1 day ago');
    });

    test('2 days uses the real plural form, "2 days ago"', () {
      expect(formatStaleness(2), '2 days ago');
    });

    test('5 days uses the real plural form, "5 days ago"', () {
      expect(formatStaleness(5), '5 days ago');
    });

    test('a genuinely negative day count (clock skew, bad data) falls back to "Today", never nonsense', () {
      expect(formatStaleness(-1), 'Today');
      expect(formatStaleness(-1).contains('-'), isFalse);
    });
  });

  group('sortByStaleness', () {
    test('ranks the oldest-sent item first', () {
      final older = WaitingOnItem(recipient: 'a@x.com', subject: 'older', sentAt: DateTime(2026, 8, 1));
      final newer = WaitingOnItem(recipient: 'b@x.com', subject: 'newer', sentAt: DateTime(2026, 8, 10));

      final result = sortByStaleness([newer, older]);

      expect(result.map((i) => i.subject).toList(), ['older', 'newer']);
    });

    test('does not mutate the input list', () {
      final a = WaitingOnItem(recipient: 'a@x.com', subject: 'A', sentAt: DateTime(2026, 8, 1));
      final b = WaitingOnItem(recipient: 'b@x.com', subject: 'B', sentAt: DateTime(2026, 8, 5));
      final original = [b, a];

      final result = sortByStaleness(original);

      expect(original.map((i) => i.subject).toList(), ['B', 'A'], reason: 'original order must survive untouched');
      expect(result.map((i) => i.subject).toList(), ['A', 'B']);
    });

    test('an empty list sorts to an empty list, not a crash', () {
      expect(sortByStaleness(const []), isEmpty);
    });
  });
}
