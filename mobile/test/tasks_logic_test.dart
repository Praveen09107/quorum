// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// The real, hand-verified mixed-status sort, confirmed in Python before
// this file was finalized:
//   A(done,2026-01-01), B(open,none), C(cancelled,2025-01-01),
//   D(open,2026-03-01), E(open,2026-02-01)
//   -> [E, D, B, A, C]
// -- done/cancelled never interleave with open regardless of their own
// deadline; a done task (A) carries the single earliest deadline in the
// whole set (2026-01-01, earlier than every open task's) and still
// sorts after every open task.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/tasks/tasks_logic.dart';

TaskData _task(String id, TaskStatus status, DateTime? deadline) => TaskData(
      taskId: id,
      title: id,
      estimatedHours: 1.0,
      deadline: deadline,
      status: status,
    );

void main() {
  group('parseTaskStatus', () {
    test('open parses correctly', () {
      expect(parseTaskStatus('open'), TaskStatus.open);
    });

    test('done parses correctly', () {
      expect(parseTaskStatus('done'), TaskStatus.done);
    });

    test('cancelled parses correctly', () {
      expect(parseTaskStatus('cancelled'), TaskStatus.cancelled);
    });

    test('THE REAL, DELIBERATE CONTRAST — an unrecognized value fails LOUD, never falls back gracefully', () {
      expect(() => parseTaskStatus('archived'), throwsArgumentError);
    });
  });

  group('statusLabel', () {
    test('open gets a real, readable label', () {
      expect(statusLabel(TaskStatus.open), 'Open');
    });

    test('done gets a real, readable label', () {
      expect(statusLabel(TaskStatus.done), 'Done');
    });

    test('cancelled gets a real, readable label', () {
      expect(statusLabel(TaskStatus.cancelled), 'Cancelled');
    });
  });

  group('formatHours -- pure display formatting, no rounding-ambiguity risk', () {
    test('a real, precise fractional value formats cleanly', () {
      expect(formatHours(2.5), '2.5h');
    });

    test('a real whole-number value still shows one decimal place, consistently', () {
      expect(formatHours(4.0), '4.0h');
    });
  });

  group('sortTasks', () {
    test('the real, hand-verified mixed-status sort', () {
      final a = _task('A', TaskStatus.done, DateTime(2026, 1, 1));
      final b = _task('B', TaskStatus.open, null);
      final c = _task('C', TaskStatus.cancelled, DateTime(2025, 1, 1));
      final d = _task('D', TaskStatus.open, DateTime(2026, 3, 1));
      final e = _task('E', TaskStatus.open, DateTime(2026, 2, 1));

      final result = sortTasks([a, b, c, d, e]);

      expect(result.map((t) => t.taskId).toList(), ['E', 'D', 'B', 'A', 'C']);
    });

    test('a done task carrying the single earliest deadline in the set still sorts after every open task', () {
      final earliestButDone = _task('done_earliest', TaskStatus.done, DateTime(2020, 1, 1));
      final openLater = _task('open_later', TaskStatus.open, DateTime(2030, 1, 1));

      final result = sortTasks([earliestButDone, openLater]);

      expect(result.map((t) => t.taskId).toList(), ['open_later', 'done_earliest']);
    });

    test('does not mutate the input list', () {
      final a = _task('A', TaskStatus.open, DateTime(2026, 3, 1));
      final b = _task('B', TaskStatus.open, DateTime(2026, 1, 1));
      final original = [a, b];

      final result = sortTasks(original);

      expect(original.map((t) => t.taskId).toList(), ['A', 'B'], reason: 'original order must survive untouched');
      expect(result.map((t) => t.taskId).toList(), ['B', 'A']);
    });

    test('an empty list sorts to an empty list, not a crash', () {
      expect(sortTasks(const []), isEmpty);
    });

    test('open tasks with a real deadline sort strictly before open tasks with none', () {
      final noDeadline = _task('none', TaskStatus.open, null);
      final withDeadline = _task('has_one', TaskStatus.open, DateTime(2026, 6, 1));

      final result = sortTasks([noDeadline, withDeadline]);

      expect(result.map((t) => t.taskId).toList(), ['has_one', 'none']);
    });

    test('done sorts strictly before cancelled, even with reversed deadlines', () {
      final cancelledEarly = _task('cancelled_early', TaskStatus.cancelled, DateTime(2020, 1, 1));
      final doneLate = _task('done_late', TaskStatus.done, DateTime(2030, 1, 1));

      final result = sortTasks([cancelledEarly, doneLate]);

      expect(result.map((t) => t.taskId).toList(), ['done_late', 'cancelled_early']);
    });
  });
}
