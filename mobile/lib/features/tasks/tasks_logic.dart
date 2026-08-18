// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// A genuinely new endpoint gap, found and fixed the same way as every
// prior one in this project: `QUORUM_DATA_CONTRACTS.md` never specified
// `GET /tasks` before this session — added as §5.17 before this file was
// built against it, and confirmed already present in this repository's
// real copy of the document before writing this file.
//
// THE DELIBERATE DESIGN CONTRAST with `MOBILE_11`'s Career Pipeline,
// confirmed directly against this repository's real schema before
// writing a line of Dart, not copied from that screen's pattern out of
// habit: `tasks.status` has a real database `CHECK` constraint --
// `CHECK (status IN ('open','done','cancelled'))`, confirmed live
// against `backend/migrations/0001_initial_schema/up.sql` (the real
// path in this repository; the batch guide's own reference,
// `backend/migrations/001_initial_schema.sql`, does not match --
// adapted, not silently ignored). This is a genuinely CLOSED contract,
// unlike `applications.status`'s confirmed-open one (`DEC-083`) -- so
// `parseTaskStatus` correctly fails LOUD on an unrecognized value,
// rather than falling back gracefully. Applying Career Pipeline's
// defensive pattern here out of habit, without re-checking what's
// actually true for THIS field's real contract, would have been exactly
// the mistake CLAUDE.md Rule 4 exists to prevent.
//
// A genuine absence of rounding risk, confirmed rather than assumed:
// `estimated_hours` is a real `NUMERIC(4,1)` column -- the database
// itself guarantees at most one decimal place, so `formatHours` is pure
// display formatting of already-precise data, not a rounding operation
// with a disputed tie-break case like `MOBILE_13`'s.

enum TaskStatus { open, done, cancelled }

class TaskData {
  final String taskId;
  final String title;
  final double estimatedHours;
  final DateTime? deadline;
  final TaskStatus status;

  const TaskData({
    required this.taskId,
    required this.title,
    required this.estimatedHours,
    required this.deadline,
    required this.status,
  });
}

/// Fails LOUD -- the deliberate opposite of Career Pipeline's
/// `statusLabel` fallback -- because `tasks.status`'s real contract is
/// genuinely closed, database-enforced. An unrecognized value here means
/// something is real and wrong upstream (a schema drift, a real bug),
/// not a legitimate new value this client should gracefully absorb.
TaskStatus parseTaskStatus(String raw) {
  switch (raw) {
    case 'open':
      return TaskStatus.open;
    case 'done':
      return TaskStatus.done;
    case 'cancelled':
      return TaskStatus.cancelled;
    default:
      throw ArgumentError('Unexpected task status: $raw — tasks.status is a closed, database-enforced set');
  }
}

String statusLabel(TaskStatus status) {
  switch (status) {
    case TaskStatus.open:
      return 'Open';
    case TaskStatus.done:
      return 'Done';
    case TaskStatus.cancelled:
      return 'Cancelled';
  }
}

/// Pure display formatting -- estimated_hours is already precise to one
/// decimal place at the database level; no rounding ambiguity exists.
String formatHours(double estimatedHours) {
  return '${estimatedHours.toStringAsFixed(1)}h';
}

int _statusOrder(TaskStatus status) {
  switch (status) {
    case TaskStatus.open:
      return 0;
    case TaskStatus.done:
      return 1;
    case TaskStatus.cancelled:
      return 2;
  }
}

/// THE REAL ORDERING RULE, hand-verified in Python before being trusted
/// in Dart: open tasks first (deadline-ascending, no-deadline last among
/// open), then done, then cancelled. Done/cancelled tasks never
/// interleave with open ones regardless of their own deadline -- a done
/// task carrying the single earliest deadline in the set still sorts
/// after every open task. Returns a genuine copy; the input list is
/// never mutated.
List<TaskData> sortTasks(List<TaskData> tasks) {
  final sorted = List<TaskData>.from(tasks);
  sorted.sort((a, b) {
    final statusCompare = _statusOrder(a.status).compareTo(_statusOrder(b.status));
    if (statusCompare != 0) return statusCompare;

    final aNoDeadline = a.deadline == null;
    final bNoDeadline = b.deadline == null;
    if (aNoDeadline != bNoDeadline) {
      return aNoDeadline ? 1 : -1;
    }
    if (aNoDeadline && bNoDeadline) return 0;
    return a.deadline!.compareTo(b.deadline!);
  });
  return sorted;
}
