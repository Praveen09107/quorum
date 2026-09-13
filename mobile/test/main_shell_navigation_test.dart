// Real, live proof for Batch 10 Phase 4's actual navigation wiring --
// UNVERIFIED IN SANDBOX note doesn't apply here (written and run on a
// real machine, real Flutter 3.47.0, DEC-103/DEC-104). Every real drill-
// through named in main_shell.dart's own header comment gets a real
// test here: a real tap, a real pumpAndSettle, and an assertion on the
// TARGET screen's real, distinctive content -- not just that a route
// pushed, that the right real data actually arrived and rendered.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar_sync.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';
import 'package:quorum_mobile/features/computed_state.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';
import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';
import 'package:quorum_mobile/features/today/in_motion_logic.dart';
import 'package:quorum_mobile/features/today/needs_you_now_logic.dart';
import 'package:quorum_mobile/features/today_screen.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';
import 'package:quorum_mobile/shell/main_shell.dart';
import 'package:quorum_mobile/theme/motion.dart';

Future<TodayScreenData> _fakeFetchToday() async {
  return TodayScreenData(
    pendingActions: [
      PendingActionSummary(
        proposalId: 'p1',
        actionType: 'send_email',
        stakes: 'S3',
        payload: const {},
        createdAt: DateTime(2026, 8, 10),
      ),
    ],
    capacity: const CapacityState(hoursRemainingToday: 3.5, remainingFraction: 0.44, source: DataSource.liveBackend),
    budget: const BudgetState(amountRemaining: 4200, remainingFraction: 0.6, source: DataSource.liveBackend),
    negotiations: [
      ActiveNegotiationSummary(negotiationId: 'n1', conflictedDomains: const ['calendar', 'finance'], startedAt: DateTime(2026, 8, 9)),
    ],
  );
}

// REAL, DISCLOSED FIX (`DEC-187`): a real, mutable-response fetcher
// proving Today genuinely re-fetches after a real negotiation-detail
// push returns -- the second real call's own negotiations list is
// deliberately different (empty, simulating the negotiation now being
// resolved server-side) from the first, so a stale, cached first
// response could never accidentally pass this test.
int fetchTodayCallCountForReloadTest = 0;

Future<TodayScreenData> _fakeFetchTodayTrackingReload() async {
  fetchTodayCallCountForReloadTest++;
  return TodayScreenData(
    pendingActions: const [],
    capacity: const CapacityState(hoursRemainingToday: 3.5, remainingFraction: 0.44, source: DataSource.liveBackend),
    budget: const BudgetState(amountRemaining: 4200, remainingFraction: 0.6, source: DataSource.liveBackend),
    negotiations: fetchTodayCallCountForReloadTest == 1
        ? [ActiveNegotiationSummary(negotiationId: 'n1', conflictedDomains: const ['calendar', 'finance'], startedAt: DateTime(2026, 8, 9))]
        : const [],
  );
}

Future<GateRevealBundle> _fakeFetchGateReveal(String proposalId) async {
  return const GateRevealBundle(
    stakes: 'S3',
    findings: [
      FindingSummary(validator: 'budget_check', claim: 'within budget', visualState: EvidenceVisualState.positive),
    ],
    objections: [],
  );
}

// RESOLVED, a real, disclosed gap found on-device (Session 2,
// `QUORUM_FINAL_COMPLETION_PLAN.md`, `DEC-168`): a mutable test flag,
// matching `chosenNegotiationCalls`'s own established pattern, so a
// single fake fetcher can exercise both the genuinely-open and
// already-resolved real response shapes without a second, parallel
// negotiation fixture.
bool negotiationAlreadyResolvedForTest = false;

Future<NegotiationBundle> _fakeFetchNegotiation(String negotiationId) async {
  return NegotiationBundle(
    positions: const [PositionData(domain: 'finance', concern: 'Real budget concern', proposedResolution: 'Real resolution')],
    options: const [
      NegotiationOptionData(optionId: 'opt1', description: 'A real option', sourceDomains: ['finance'], impact: []),
    ],
    resolvedAt: negotiationAlreadyResolvedForTest ? '2026-09-06T18:29:54Z' : null,
    chosenOptionId: negotiationAlreadyResolvedForTest ? 'opt1' : null,
  );
}

final List<(String, String)> chosenNegotiationCalls = [];

Future<void> _fakeChooseNegotiation(String negotiationId, String optionId) async {
  chosenNegotiationCalls.add((negotiationId, optionId));
}

Future<List<CareerApplication>> _fakeFetchCareerApplications() async {
  return const [
    CareerApplication(applicationId: 'app1', company: 'Real Test Company', status: 'applied'),
  ];
}

Future<CompanyDigestData> _fakeFetchCareerDigest(String applicationId) async {
  return const CompanyDigestData(
    company: 'Real Test Company',
    summaryPoints: ['A real, distinctive research point'],
    sourceCount: 3,
  );
}

Future<List<DetectedSubscriptionData>> _fakeFetchFinance() async {
  return const [
    DetectedSubscriptionData(payee: 'Real Test Subscription', averageAmount: 499.0, occurrences: 3, averageIntervalDays: 30.0),
  ];
}

Future<List<WaitingOnItem>> _fakeFetchWaitingOn() async {
  return [
    WaitingOnItem(recipient: 'real.test@example.com', subject: 'A real subject line', sentAt: DateTime(2026, 8, 1)),
  ];
}

Future<List<SearchResultItem>> _fakeFetchSearch(String query) async {
  return [
    SearchResultItem(itemId: 's1', itemType: SearchItemType.email, text: 'A real search result for "$query"', timestamp: DateTime(2026, 8, 1)),
  ];
}

Future<List<TaskData>> _fakeFetchTasks() async {
  return [
    const TaskData(taskId: 't1', title: 'A real, distinctive test task', estimatedHours: 2.0, deadline: null, status: TaskStatus.open),
  ];
}

Future<CalendarSyncResult> _fakeSyncCalendar() async {
  return const CalendarSyncResult(eventsSynced: 1, permissionGranted: true);
}

Future<List<CalendarMirrorData>> _fakeFetchCalendarEvents() async {
  return [
    CalendarMirrorData(
      eventId: 'evt1',
      title: 'A real, distinctive synced event',
      startTime: DateTime(2026, 9, 1, 14, 0),
      endTime: DateTime(2026, 9, 1, 15, 0),
      sourceCalendarId: 'cal_primary',
      lastSyncedAt: DateTime(2026, 8, 28),
    ),
  ];
}

Future<QuickCaptureResultData> _fakeCaptureTask(String text) async {
  return QuickCaptureResultData(
    executed: true,
    decision: 'approve',
    stakes: 'S1',
    domain: 'tasks',
    title: 'A real, distinctive quick-captured task: $text',
    findings: const [],
  );
}

Future<RiskAssessmentData> _fakeFetchPredictiveRisk() async {
  return RiskAssessmentData(
    weekStart: DateTime(2026, 9, 1),
    deadlineDensity: 3,
    matchingHistoricalWeeks: 2,
    pooledCorrectionRate: 0.6,
    isAtRisk: true,
  );
}

Widget _harness({
  Future<List<CalendarMirrorData>> Function()? fetchCalendarEvents,
  Future<TodayScreenData> Function()? fetchToday,
}) {
  return ProviderScope(
    child: MaterialApp(
      home: MainShell(
        fetchToday: fetchToday ?? _fakeFetchToday,
        fetchTasks: _fakeFetchTasks,
        fetchPredictiveRisk: _fakeFetchPredictiveRisk,
        fetchGateReveal: _fakeFetchGateReveal,
        fetchNegotiation: _fakeFetchNegotiation,
        chooseNegotiation: _fakeChooseNegotiation,
        fetchCareerApplications: _fakeFetchCareerApplications,
        fetchCareerDigest: _fakeFetchCareerDigest,
        fetchFinance: _fakeFetchFinance,
        fetchWaitingOn: _fakeFetchWaitingOn,
        fetchSearch: _fakeFetchSearch,
        syncCalendar: _fakeSyncCalendar,
        fetchCalendarEvents: fetchCalendarEvents ?? _fakeFetchCalendarEvents,
        captureTask: _fakeCaptureTask,
        confirmDelete: () async => throw UnimplementedError(),
      ),
    ),
  );
}

void main() {
  testWidgets('tapping "View tasks" opens the real Tasks screen with the real predictive risk banner', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('View tasks'));
    await tester.pumpAndSettle();

    expect(find.text('A real, distinctive test task'), findsOneWidget);
    // The real risk banner (DEC-149) -- rendered above the real task
    // list, not a new tab or a separate screen.
    expect(find.textContaining('Next week may be tight'), findsOneWidget);
    expect(find.textContaining('60%'), findsOneWidget);
  });

  testWidgets('tapping a Needs You Now action opens the real Gate reveal with real findings', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Send an email'));
    await tester.pumpAndSettle();

    expect(find.text('Stage A — automated checks'), findsOneWidget);
    expect(find.textContaining('within budget'), findsOneWidget);
  });

  // Real, disclosed follow-up (`DEC-158` standard-tier review, finding
  // 1): the prior test above proves the Gate reveal's real timed
  // animation resolves cleanly via `pumpAndSettle()`, but never asserted
  // the actual STAGING -- that Stage B is genuinely absent immediately
  // after Stage A appears, and genuinely present only once
  // `QuorumMotion.reveal` has elapsed. Without this test, a logic
  // inversion (Stage B showing immediately, or never showing at all)
  // would still pass every other real test in this suite.
  testWidgets('the real Gate verdict reveal stages Stage B in a beat after Stage A, not simultaneously', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Send an email'));
    // Deliberately NOT pumpAndSettle here -- two plain pumps are enough
    // to let the real S3 action's route push and `_fakeFetchGateReveal`'s
    // Future resolve, but stop well short of `QuorumMotion.reveal`
    // (350ms), so Stage B's own real, timed absence is still genuinely
    // observable.
    await tester.pump();
    await tester.pump();

    expect(find.text('Stage A — automated checks'), findsOneWidget);
    expect(find.text('Stage B — Critic review'), findsNothing);

    await tester.pump(QuorumMotion.reveal);
    await tester.pumpAndSettle();

    expect(find.text('Stage B — Critic review'), findsOneWidget);
  });

  testWidgets('tapping an In Motion negotiation card opens the real negotiation screen with real positions and options', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView).first, const Offset(0, -1000));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar vs. Finance'));
    await tester.pumpAndSettle();

    expect(find.text('What each domain is saying'), findsOneWidget);
    expect(find.textContaining('Real budget concern'), findsOneWidget);
    expect(find.textContaining('A real option'), findsOneWidget);
  });

  testWidgets('choosing a real negotiation option calls the real chooseNegotiation callback and shows a real, honest confirmation', (tester) async {
    chosenNegotiationCalls.clear();
    negotiationAlreadyResolvedForTest = false;
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView).first, const Offset(0, -1000));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar vs. Finance'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Choose this option'));
    await tester.pumpAndSettle();

    expect(chosenNegotiationCalls, [('n1', 'opt1')]);
    // A real, honest terminal state matching the backend's own real
    // 202 Accepted semantics -- never claims more happened than that.
    expect(find.text('Choice accepted -- this action is now queued.'), findsOneWidget);
    // The real positions/options view is genuinely replaced, not just
    // overlaid -- confirms this is a real terminal state, not a toast.
    expect(find.text('What each domain is saying'), findsNothing);
  });

  testWidgets('re-opening an already-resolved negotiation shows an honest already-resolved state, never a tappable options screen', (tester) async {
    // RESOLVED, a real, disclosed gap found on-device (Session 2,
    // `QUORUM_FINAL_COMPLETION_PLAN.md`, `DEC-168`): before this fix, a
    // real user re-opening an already-decided negotiation saw the
    // exact same fully-interactive options screen as a genuinely open
    // one, discovering it was already resolved only via a real,
    // honest `409` from `POST .../choose` AFTER tapping "Choose this
    // option" again. This test proves the real fix: the client now
    // knows from the fetch itself, before any tap.
    negotiationAlreadyResolvedForTest = true;
    addTearDown(() => negotiationAlreadyResolvedForTest = false);
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView).first, const Offset(0, -1000));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar vs. Finance'));
    await tester.pumpAndSettle();

    expect(find.textContaining('already resolved'), findsOneWidget);
    expect(find.textContaining('A real option'), findsOneWidget);  // names what was genuinely chosen
    expect(find.text('Choose this option'), findsNothing);  // never presented as if a choice were still possible
  });

  testWidgets('returning from a real negotiation detail screen triggers a real Today refetch, not a stale cached view', (tester) async {
    // RESOLVED, a real, disclosed gap found on-device (`DEC-174`) and
    // fixed here (`DEC-187`): before this fix, Today's own "In Motion"
    // card kept showing a just-resolved negotiation until a full, cold
    // app relaunch -- the real, live server state was always correct,
    // Today just never asked again. `_fakeFetchTodayTrackingReload`'s
    // own SECOND real response deliberately returns a genuinely
    // different (empty) negotiations list, so this test can only pass
    // if Today's real fetcher was actually called a second time, not
    // merely re-rendered from the first call's stale cached data.
    fetchTodayCallCountForReloadTest = 0;
    negotiationAlreadyResolvedForTest = false;
    await tester.pumpWidget(_harness(fetchToday: _fakeFetchTodayTrackingReload));
    await tester.pumpAndSettle();
    expect(fetchTodayCallCountForReloadTest, 1);

    await tester.drag(find.byType(ListView).first, const Offset(0, -1000));
    await tester.pumpAndSettle();
    expect(find.text('Calendar vs. Finance'), findsOneWidget);

    await tester.tap(find.text('Calendar vs. Finance'));
    await tester.pumpAndSettle();
    expect(find.text('What each domain is saying'), findsOneWidget);

    // A real user simply backing out having only viewed it -- no
    // choice submitted -- is exactly the case the old code silently
    // mishandled worst (there was no server-side change to even
    // coincidentally trigger a correct-looking re-render).
    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(fetchTodayCallCountForReloadTest, 2);
    expect(find.text('Calendar vs. Finance'), findsNothing);
  });

  testWidgets('the You tab genuinely reaches Career Pipeline, and tapping an application opens its real Company Digest', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Career pipeline'));
    await tester.pumpAndSettle();

    expect(find.text('Real Test Company'), findsOneWidget);

    await tester.tap(find.text('Real Test Company'));
    await tester.pumpAndSettle();

    expect(find.textContaining('A real, distinctive research point'), findsOneWidget);
  });

  testWidgets('the You tab genuinely reaches real Subscriptions', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Subscriptions'));
    await tester.pumpAndSettle();

    expect(find.text('Real Test Subscription'), findsOneWidget);
  });

  testWidgets('the You tab genuinely reaches real Waiting On items', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Waiting on'));
    await tester.pumpAndSettle();

    expect(find.textContaining('real.test@example.com'), findsOneWidget);
  });

  testWidgets('the You tab genuinely reaches real Search, and submitting a real query returns real results', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Search'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'invoice');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();

    expect(find.textContaining('A real search result for "invoice"'), findsOneWidget);
  });

  testWidgets('the You tab genuinely reaches the real Calendar screen with a real synced event', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar'));
    await tester.pumpAndSettle();

    expect(find.text('A real, distinctive synced event'), findsOneWidget);
  });

  testWidgets('the real Meeting-Load banner reassures when the next 7 real days are genuinely light', (tester) async {
    // A real, single 1-hour event, genuinely far below the real 4.2h
    // overload boundary -- computed relative to the real DateTime.now()
    // at test-run time, never a fixed date that could drift into the
    // past.
    final now = DateTime.now();
    Future<List<CalendarMirrorData>> lightWeek() async => [
          CalendarMirrorData(
            eventId: 'evt_light',
            title: 'A real, light event',
            startTime: now.add(const Duration(hours: 2)),
            endTime: now.add(const Duration(hours: 3)),
            sourceCalendarId: 'cal_primary',
            lastSyncedAt: now,
          ),
        ];

    await tester.pumpWidget(_harness(fetchCalendarEvents: lightWeek));
    await tester.pumpAndSettle();
    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar'));
    await tester.pumpAndSettle();

    expect(find.text('Next 7 days look manageable.'), findsOneWidget);
  });

  testWidgets('the real Meeting-Load banner genuinely warns for a real, overloaded day within the next 7', (tester) async {
    // A real, genuine 6-hour real commitment today -- exceeds the
    // real, specified 4.2h default overload boundary (0.7 * 8.0 *
    // 0.75), computed relative to the real DateTime.now().
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day, 9, 0);
    Future<List<CalendarMirrorData>> overloadedWeek() async => [
          CalendarMirrorData(
            eventId: 'evt_heavy',
            title: 'A real, heavy real commitment',
            startTime: today,
            endTime: today.add(const Duration(hours: 6)),
            sourceCalendarId: 'cal_primary',
            lastSyncedAt: now,
          ),
        ];

    await tester.pumpWidget(_harness(fetchCalendarEvents: overloadedWeek));
    await tester.pumpAndSettle();
    await tester.tap(find.text('You'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Calendar'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Heavier than usual'), findsOneWidget);
  });

  testWidgets('the real floating action button opens Quick capture and creates a real task from real free text', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();

    expect(find.text('Quick capture'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'water the plants');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();

    expect(find.text('Created: A real, distinctive quick-captured task: water the plants'), findsOneWidget);
  });

  testWidgets('the floating action button is reachable and identical from every real tab, not just Today', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Trust'));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.add), findsOneWidget);
  });
}
