// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// Hand-verified in Python before this file was finalized:
//   2-domain: 'Calendar vs. Finance'
//   3-domain: 'Calendar vs. Finance vs. Tasks'
//   empty: 'Unknown conflict'
//   single-domain edge case: 'Calendar' (no "vs." separator)

import 'package:test/test.dart';

import 'package:quorum_mobile/features/today/in_motion_logic.dart';

DateTime _day(int n) => DateTime(2026, 8, n);

void main() {
  group('describeConflict', () {
    test('the real two-domain case, using the exact backend domain literals', () {
      expect(describeConflict(['calendar', 'finance']), 'Calendar vs. Finance');
    });

    test('the real three-domain case, using the exact backend domain literals', () {
      expect(describeConflict(['calendar', 'finance', 'tasks']), 'Calendar vs. Finance vs. Tasks');
    });

    test('a single-domain edge case has no "vs." separator', () {
      expect(describeConflict(['calendar']), 'Calendar');
      expect(describeConflict(['calendar']).contains('vs.'), isFalse);
    });

    test('an empty domain list falls back to a genuine, honest "Unknown conflict"', () {
      expect(describeConflict(const []), 'Unknown conflict');
    });
  });

  group('sortByStaleness', () {
    test('ranks the OLDEST-started negotiation first', () {
      final older = ActiveNegotiationSummary(negotiationId: 'older', conflictedDomains: const ['calendar', 'finance'], startedAt: _day(1));
      final newer = ActiveNegotiationSummary(negotiationId: 'newer', conflictedDomains: const ['calendar', 'tasks'], startedAt: _day(5));

      final result = sortByStaleness([newer, older]);

      expect(result.map((n) => n.negotiationId).toList(), ['older', 'newer']);
    });

    test('does not mutate the input list', () {
      final a = ActiveNegotiationSummary(negotiationId: 'A', conflictedDomains: const ['calendar', 'finance'], startedAt: _day(1));
      final b = ActiveNegotiationSummary(negotiationId: 'B', conflictedDomains: const ['calendar', 'tasks'], startedAt: _day(2));
      final original = [b, a];

      final result = sortByStaleness(original);

      expect(original.map((n) => n.negotiationId).toList(), ['B', 'A'], reason: 'original order must survive untouched');
      expect(result.map((n) => n.negotiationId).toList(), ['A', 'B']);
    });

    test('three real negotiations sort into a full, correct staleness order', () {
      final a = ActiveNegotiationSummary(negotiationId: 'A', conflictedDomains: const ['calendar', 'finance'], startedAt: _day(3));
      final b = ActiveNegotiationSummary(negotiationId: 'B', conflictedDomains: const ['calendar', 'finance', 'tasks'], startedAt: _day(1));
      final c = ActiveNegotiationSummary(negotiationId: 'C', conflictedDomains: const ['finance', 'tasks'], startedAt: _day(2));

      final result = sortByStaleness([a, b, c]);

      expect(result.map((n) => n.negotiationId).toList(), ['B', 'C', 'A']);
    });
  });
}
