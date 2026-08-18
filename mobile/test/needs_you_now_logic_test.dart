// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// The hand-verified mixed-case sort below matches the exact Python
// reimplementation run before this file was finalized:
//   items = A(S2,day1), B(S3,day5), C(S3,day2), D(S1,day3)
//   Computed order: ['C', 'B', 'A', 'D']  -- PASS

import 'package:test/test.dart';

import 'package:quorum_mobile/features/today/needs_you_now_logic.dart';
import 'package:quorum_mobile/gate/action_types.dart';

DateTime _day(int n) => DateTime(2026, 8, n);

void main() {
  group('sortByUrgency', () {
    test('the real, hand-verified mixed case: higher stakes first, oldest-first tiebreak', () {
      final a = PendingActionSummary(proposalId: 'A', actionType: 'create_task', stakes: 'S2', payload: const {}, createdAt: _day(1));
      final b = PendingActionSummary(proposalId: 'B', actionType: 'send_email', stakes: 'S3', payload: const {}, createdAt: _day(5));
      final c = PendingActionSummary(proposalId: 'C', actionType: 'send_email', stakes: 'S3', payload: const {}, createdAt: _day(2));
      final d = PendingActionSummary(proposalId: 'D', actionType: 'create_note', stakes: 'S1', payload: const {}, createdAt: _day(3));

      final result = sortByUrgency([a, b, c, d]);

      expect(result.map((x) => x.proposalId).toList(), ['C', 'B', 'A', 'D']);
    });

    test('does not mutate the input list', () {
      final a = PendingActionSummary(proposalId: 'A', actionType: 'create_task', stakes: 'S1', payload: const {}, createdAt: _day(1));
      final b = PendingActionSummary(proposalId: 'B', actionType: 'send_email', stakes: 'S3', payload: const {}, createdAt: _day(2));
      final original = [a, b];

      final result = sortByUrgency(original);

      expect(original.map((x) => x.proposalId).toList(), ['A', 'B'], reason: 'original order must survive untouched');
      expect(result.map((x) => x.proposalId).toList(), ['B', 'A']);
      expect(identical(result, original), isFalse);
    });

    test('an empty list sorts to an empty list, not a crash', () {
      expect(sortByUrgency(const []), isEmpty);
    });

    test('a single-item list is returned unchanged', () {
      final only = PendingActionSummary(proposalId: 'X', actionType: 'create_task', stakes: 'S1', payload: const {}, createdAt: _day(1));
      final result = sortByUrgency([only]);
      expect(result.length, 1);
      expect(result.first.proposalId, 'X');
    });

    test('same stakes, different age -- the older one wins', () {
      final older = PendingActionSummary(proposalId: 'older', actionType: 'create_task', stakes: 'S2', payload: const {}, createdAt: _day(1));
      final newer = PendingActionSummary(proposalId: 'newer', actionType: 'create_task', stakes: 'S2', payload: const {}, createdAt: _day(5));

      final result = sortByUrgency([newer, older]);

      expect(result.map((x) => x.proposalId).toList(), ['older', 'newer']);
    });
  });

  group('summarizeForNeedsYouNow', () {
    test('a recognized action_type gets a real, readable headline', () {
      final action = PendingActionSummary(proposalId: 'A', actionType: 'send_email', stakes: 'S3', payload: const {}, createdAt: _day(1));
      final summary = summarizeForNeedsYouNow(action);
      expect(summary.headline, 'Send an email');
      expect(summary.stakesLabel, 'Needs your approval');
    });

    test('an unrecognized action_type never shows raw jargon -- de-snaked fallback', () {
      final action = PendingActionSummary(proposalId: 'A', actionType: 'some_future_action_type', stakes: 'S1', payload: const {}, createdAt: _day(1));
      final summary = summarizeForNeedsYouNow(action);
      expect(summary.headline, 'Some Future Action Type');
      expect(summary.headline.contains('_'), isFalse);
    });

    test('a missing/empty payload never throws -- summarization does not depend on payload contents', () {
      final action = PendingActionSummary(proposalId: 'A', actionType: 'create_task', stakes: 'S2', payload: const {}, createdAt: _day(1));
      expect(() => summarizeForNeedsYouNow(action), returnsNormally);
    });

    test('every real stakes level gets a distinct, correct label', () {
      final stakesToExpected = {
        'S3': 'Needs your approval',
        'S2': 'Needs review',
        'S1': 'Low-stakes, ready to go',
        'S0': 'Informational',
      };
      for (final entry in stakesToExpected.entries) {
        final action = PendingActionSummary(proposalId: 'A', actionType: 'create_task', stakes: entry.key, payload: const {}, createdAt: _day(1));
        expect(summarizeForNeedsYouNow(action).stakesLabel, entry.value, reason: 'stakes ${entry.key}');
      }
    });
  });

  group('readableActionType -- all 11 real ActionType values, cross-checked against the backend', () {
    test('covers every real backend ActionType with a genuinely readable label', () {
      const realTypes = [
        'send_email',
        'create_calendar_event_external',
        'create_calendar_event_local',
        'create_task',
        'update_task',
        'log_expense',
        'update_budget',
        'create_note',
        'update_application_status',
        'archive_email',
        'label_email',
      ];
      for (final type in realTypes) {
        final label = readableActionType(type);
        expect(label.contains('_'), isFalse, reason: '$type should never leak a raw underscore');
        expect(label.isNotEmpty, isTrue);
      }
    });
  });
}
