// Real tests for features/activity/activity_logic.dart (`DEC-205`,
// product rebuild). Zero Flutter dependencies, `dart test` is the
// real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/activity/activity_logic.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

LoggedActionData _action({
  required String id,
  required DateTime timestamp,
  String outcome = 'approved_unchanged',
  String actionType = 'create_task',
  String stakes = 'S1',
  String? domain = 'tasks',
}) {
  return LoggedActionData(
    actionId: id,
    timestamp: timestamp,
    outcome: outcome,
    description: 'A real action $id',
    actionType: actionType,
    stakes: stakes,
    domain: domain,
  );
}

void main() {
  group('mergeActivityTimeline', () {
    test('merges three real, already-sorted buckets into one real chronological order', () {
      final now = DateTime(2026, 10, 6, 12, 0);
      final feed = HonestyFeedData(
        total: 3,
        successRate: 1.0,
        successes: [_action(id: 's1', timestamp: now.subtract(const Duration(hours: 1)))],
        failuresAndCatches: [_action(id: 'f1', timestamp: now)],
        genuinelyUncertain: [_action(id: 'u1', timestamp: now.subtract(const Duration(hours: 2)))],
      );

      final merged = mergeActivityTimeline(feed);

      expect(merged.map((a) => a.actionId).toList(), ['f1', 's1', 'u1']);
    });

    test('a genuinely empty feed merges to an honest empty list, not a crash', () {
      const feed = HonestyFeedData(total: 0, successRate: null, successes: [], failuresAndCatches: [], genuinelyUncertain: []);
      expect(mergeActivityTimeline(feed), isEmpty);
    });

    test('preserves real, correct order within a single bucket containing multiple real rows', () {
      final now = DateTime(2026, 10, 6, 12, 0);
      final feed = HonestyFeedData(
        total: 2,
        successRate: 1.0,
        successes: [
          _action(id: 'newer', timestamp: now),
          _action(id: 'older', timestamp: now.subtract(const Duration(hours: 1))),
        ],
        failuresAndCatches: const [],
        genuinelyUncertain: const [],
      );

      expect(mergeActivityTimeline(feed).map((a) => a.actionId).toList(), ['newer', 'older']);
    });
  });

  group('groupActivityByDay', () {
    test('groups real actions on the same real calendar day together, in order', () {
      final actions = [
        _action(id: 'a1', timestamp: DateTime(2026, 10, 6, 9, 0)),
        _action(id: 'a2', timestamp: DateTime(2026, 10, 6, 18, 0)),
        _action(id: 'a3', timestamp: DateTime(2026, 10, 5, 9, 0)),
      ];

      final groups = groupActivityByDay(actions);

      expect(groups.length, 2);
      expect(groups[0].day, DateTime(2026, 10, 6));
      expect(groups[0].actions.map((a) => a.actionId).toList(), ['a1', 'a2']);
      expect(groups[1].day, DateTime(2026, 10, 5));
    });

    test('an empty real list produces an honestly empty group list', () {
      expect(groupActivityByDay([]), isEmpty);
    });
  });

  group('applyActivityFilter', () {
    final actions = [
      _action(id: 'email1', timestamp: DateTime(2026, 10, 6), domain: 'email', stakes: 'S3', outcome: 'caught_by_gate'),
      _action(id: 'task1', timestamp: DateTime(2026, 10, 6), domain: 'tasks', stakes: 'S1', outcome: 'approved_unchanged'),
      _action(id: 'note1', timestamp: DateTime(2026, 10, 6), domain: null, stakes: 'S1', outcome: 'approved_unchanged'),
    ];

    test('ActivityFilter.none is genuinely inactive and returns every real row unchanged', () {
      expect(ActivityFilter.none.isActive, isFalse);
      expect(applyActivityFilter(actions, ActivityFilter.none), hasLength(3));
    });

    test('a real domain filter keeps only matching rows', () {
      final result = applyActivityFilter(actions, const ActivityFilter(domain: 'email'));
      expect(result.map((a) => a.actionId).toList(), ['email1']);
    });

    test('a real stakes filter keeps only matching rows', () {
      final result = applyActivityFilter(actions, const ActivityFilter(stakes: 'S3'));
      expect(result.map((a) => a.actionId).toList(), ['email1']);
    });

    test('a real outcome filter keeps only matching rows', () {
      final result = applyActivityFilter(actions, const ActivityFilter(outcome: 'caught_by_gate'));
      expect(result.map((a) => a.actionId).toList(), ['email1']);
    });

    test('matchUnassignedDomain reaches a real, genuinely domain-less row (e.g. CREATE_NOTE), never silently excluded', () {
      final result = applyActivityFilter(actions, const ActivityFilter(matchUnassignedDomain: true));
      expect(result.map((a) => a.actionId).toList(), ['note1']);
    });

    test('multiple real filters combine with real, strict AND semantics', () {
      final result = applyActivityFilter(actions, const ActivityFilter(domain: 'tasks', stakes: 'S3'));
      expect(result, isEmpty);
    });
  });

  group('formatActivityDayHeader', () {
    final today = DateTime(2026, 10, 6);

    test('the real current day reads as Today', () {
      expect(formatActivityDayHeader(today, today), 'Today');
    });

    test('exactly one real day back reads as Yesterday', () {
      expect(formatActivityDayHeader(DateTime(2026, 10, 5), today), 'Yesterday');
    });

    test('anything further back is a real, plain, zero-padded date', () {
      expect(formatActivityDayHeader(DateTime(2026, 9, 1), today), '2026-09-01');
    });
  });
}
