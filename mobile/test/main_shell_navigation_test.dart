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

import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';
import 'package:quorum_mobile/features/computed_state.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';
import 'package:quorum_mobile/features/today/in_motion_logic.dart';
import 'package:quorum_mobile/features/today/needs_you_now_logic.dart';
import 'package:quorum_mobile/features/today_screen.dart';
import 'package:quorum_mobile/features/waiting_on/waiting_on_logic.dart';
import 'package:quorum_mobile/shell/main_shell.dart';

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

Future<GateRevealBundle> _fakeFetchGateReveal(String proposalId) async {
  return const GateRevealBundle(
    findings: [
      FindingSummary(validator: 'budget_check', claim: 'within budget', visualState: EvidenceVisualState.positive),
    ],
    objections: [],
  );
}

Future<NegotiationBundle> _fakeFetchNegotiation(String negotiationId) async {
  return const NegotiationBundle(
    positions: [PositionData(domain: 'finance', concern: 'Real budget concern', proposedResolution: 'Real resolution')],
    options: [
      NegotiationOptionData(optionId: 'opt1', description: 'A real option', sourceDomains: ['finance'], impact: []),
    ],
  );
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

Widget _harness() {
  return ProviderScope(
    child: MaterialApp(
      home: MainShell(
        fetchToday: _fakeFetchToday,
        fetchGateReveal: _fakeFetchGateReveal,
        fetchNegotiation: _fakeFetchNegotiation,
        fetchCareerApplications: _fakeFetchCareerApplications,
        fetchCareerDigest: _fakeFetchCareerDigest,
        fetchFinance: _fakeFetchFinance,
        fetchWaitingOn: _fakeFetchWaitingOn,
        fetchSearch: _fakeFetchSearch,
        confirmDelete: () async => throw UnimplementedError(),
      ),
    ),
  );
}

void main() {
  testWidgets('tapping a Needs You Now action opens the real Gate reveal with real findings', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Send an email'));
    await tester.pumpAndSettle();

    expect(find.text('Stage A — automated checks'), findsOneWidget);
    expect(find.textContaining('within budget'), findsOneWidget);
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
}
