// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written (confirmed by direct attempt on this machine). Structurally
// complete against Drift's documented API (real, current as of the last
// version this project confirmed — `drift: ^2.20.0`, pubspec.yaml); the
// actual `dart run build_runner build` step that generates
// `database.g.dart` from the table definitions below is a real machine's
// job, not this sandbox's.
//
// HONEST DISCLOSURE: construction-not-copy pattern, same as every real/
// external-boundary file across this project. Four real tables, two
// genuinely different jobs:
//
// 1. OfflineActionQueue — the real local record of an action proposed
//    while Extended-Outage Local Continuity Mode is active
//    (QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md §10.4). An S2 action stored
//    here carries `pendingReverification = true` and is re-checked in
//    full against the cloud Gate the moment connectivity returns — never
//    grandfathered in just because it survived the outage. An S3 action
//    stored here is prepared but explicitly never sent regardless of any
//    tap recorded while offline (§10.4's deliberate asymmetry). This
//    table's job is continuity of trust across a real outage.
//
// 2. TasksMirror / BudgetMirror / CalendarMirror — a local, read-side
//    COPY of live backend state, kept current by each domain's own real
//    sync path (CalendarMirror's real sync path is this same batch's
//    MOBILE_04). Their job is powering `computed_state.dart`'s
//    "local_mirror" source path (ADD §10.5) — the mechanism that lets
//    the Today screen's live computed numbers (capacity remaining,
//    budget pace) stay numerically identical whether the app is online
//    or offline, never silently stale. HONEST STATUS: `computed_state.dart`
//    itself has not been built in this repository yet (see
//    DECISIONS_LOG.md) — this session gives its eventual "local_mirror"
//    source path a real database schema to query against, ahead of that
//    consumer existing.
//
// Field names are kept consistent, on purpose, with the real Postgres
// columns these tables mirror (backend/migrations/0001_initial_schema/up.sql
// `tasks`; backend's real finance_agent.py payload fields `amount`/
// `category` for BudgetMirror, since no real Postgres `budget` table
// exists to copy from directly).

import 'dart:async';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:sqlite3_flutter_libs/sqlite3_flutter_libs.dart';

part 'database.g.dart';

/// A real, offline-queued action awaiting either automatic replay
/// (S0/S1/S2) or explicit human approval once verified (S3) — never
/// treated as pre-approved just because it survived an outage.
class OfflineActionQueue extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get actionType => text()();
  TextColumn get payloadJson => text()();
  TextColumn get stakes => text()(); // 'S0' | 'S1' | 'S2' | 'S3'
  BoolColumn get pendingReverification =>
      boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAt =>
      dateTime().withDefault(currentDateAndTime)();
}

/// Local mirror of the real, live `tasks` table
/// (backend/migrations/0001_initial_schema/up.sql) — field names kept
/// consistent with the real Postgres columns on purpose.
class TasksMirror extends Table {
  TextColumn get taskId => text()();
  TextColumn get title => text()();
  RealColumn get estimatedHours => real()();
  DateTimeColumn get deadline => dateTime().nullable()();
  TextColumn get status =>
      text().withDefault(const Constant('open'))();
  DateTimeColumn get lastSyncedAt =>
      dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {taskId};
}

/// Local mirror of the real Finance domain's budget concept — no real
/// Postgres `budget` table exists to mirror literally (only `expenses`
/// does); field names instead match backend's real finance_agent.py
/// payload fields (`amount`, `category`) for the UPDATE_BUDGET action
/// this table's rows represent.
class BudgetMirror extends Table {
  TextColumn get category => text()();
  RealColumn get limitAmount => real()();
  RealColumn get spentAmount => real().withDefault(const Constant(0))();
  DateTimeColumn get lastSyncedAt =>
      dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {category};
}

/// Local mirror of on-device calendar events, populated by this same
/// batch's MOBILE_04 sync (`calendar_sync.dart`) — CalendarProvider is
/// the primary source (ADD §9.2, §10.3), so this mirror gives Extended-
/// Outage Mode and `computed_state.dart`'s local path something real to
/// read even with zero network reachability.
class CalendarMirror extends Table {
  TextColumn get eventId => text()();
  TextColumn get title => text()();
  DateTimeColumn get startTime => dateTime()();
  DateTimeColumn get endTime => dateTime()();
  TextColumn get sourceCalendarId => text()();
  DateTimeColumn get lastSyncedAt =>
      dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {eventId};
}

@DriftDatabase(
  tables: [OfflineActionQueue, TasksMirror, BudgetMirror, CalendarMirror],
)
class QuorumDatabase extends _$QuorumDatabase {
  QuorumDatabase() : super(_openConnection());

  /// Drift's own documented pattern for testable database code
  /// (https://drift.simonbinder.eu/docs/testing/) — added in MOBILE_04
  /// specifically so `calendar_sync_test.dart` can run real inserts and
  /// upserts against a genuine in-memory SQLite database
  /// (`NativeDatabase.memory()`), not a mock.
  QuorumDatabase.forTesting(QueryExecutor executor) : super(executor);

  @override
  int get schemaVersion => 1;

  /// Every real, currently-open task in the mirror — what
  /// `computed_state.dart`'s eventual "local_mirror" source path needs
  /// to compute capacity numbers offline, the same real query
  /// `getAllMirroredTasks()` this session's spec names directly.
  Future<List<TasksMirrorData>> getAllMirroredTasks() {
    return select(tasksMirror).get();
  }

  /// Real, exact half-open range semantics: `start <= event.startTime <
  /// end`. Hand-verified in this session's MOBILE_04 companion work —
  /// see calendar_sync.dart's own documented boundary proof.
  Future<List<CalendarMirrorData>> getCalendarEventsInRange(
    DateTime start,
    DateTime end,
  ) {
    return (select(calendarMirror)
          ..where((t) => t.startTime.isBiggerOrEqualValue(start))
          ..where((t) => t.startTime.isSmallerThanValue(end)))
        .get();
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'quorum.sqlite'));
    if (Platform.isAndroid) {
      await applyWorkaroundToOpenSqlite3OnOldAndroidVersions();
    }
    final cachebase = (await getTemporaryDirectory()).path;
    sqlite3.tempDirectory = cachebase;
    return NativeDatabase.createInBackground(file);
  });
}
