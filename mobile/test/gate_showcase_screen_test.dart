// Real widget tests for features/gate_showcase/gate_showcase_screen.dart
// (`DEC-193`, product rebuild Block E).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/gate_showcase/gate_showcase_logic.dart';
import 'package:quorum_mobile/features/gate_showcase/gate_showcase_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

const _validators = [
  GateValidatorData(
    name: 'ProvenanceCheck',
    functionName: 'provenance_check',
    description: 'Checks the claimed source genuinely exists.',
    evidenceSource: 'database lookup',
    wired: true,
  ),
  GateValidatorData(
    name: 'PIILeakCheck',
    functionName: 'pii_leak_check',
    description: 'Checks for leaked personal information.',
    evidenceSource: 'regex scan over the draft body',
    wired: false,
  ),
];

const _stats = GateStatsData(
  totalResolved: 4,
  stakesCounts: {'S1': 2, 'S3': 2},
  successCount: 2,
  caughtCount: 1,
  rejectedCount: 1,
  uncertainCount: 0,
  catchRate: 0.5,
  rowsWithRecordedTimeline: 4,
  stageBRanCount: 1,
  revisedCount: 1,
  quotaUsed: 11,
  quotaLimit: 20,
);

Widget _harness({
  required Future<List<GateValidatorData>> Function() fetchValidators,
  required Future<GateStatsData> Function() fetchStats,
}) {
  return MaterialApp(
    theme: buildQuorumDarkTheme(),
    home: GateShowcaseScreen(fetchValidators: fetchValidators, fetchStats: fetchStats),
  );
}

void main() {
  testWidgets('renders the real validator roster, honestly distinguishing wired from not wired', (tester) async {
    await tester.pumpWidget(_harness(
      fetchValidators: () async => _validators,
      fetchStats: () async => _stats,
    ));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('ProvenanceCheck'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('ProvenanceCheck'), findsOneWidget);
    expect(find.text('Wired'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('PIILeakCheck'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('PIILeakCheck'), findsOneWidget);
    expect(find.text('Not wired'), findsOneWidget);
  });

  testWidgets('renders real live stats, including the stakes breakdown', (tester) async {
    await tester.pumpWidget(_harness(
      fetchValidators: () async => _validators,
      fetchStats: () async => _stats,
    ));
    await tester.pumpAndSettle();

    expect(find.text('4'), findsOneWidget);
    expect(find.text('50%'), findsOneWidget);
    expect(find.text('S1'), findsOneWidget);
    expect(find.text('S3'), findsOneWidget);
  });

  testWidgets('shows a real, honest error state on a real fetch failure, not a crash', (tester) async {
    await tester.pumpWidget(_harness(
      fetchValidators: () async => throw Exception('network down'),
      fetchStats: () async => _stats,
    ));
    await tester.pumpAndSettle();

    expect(find.textContaining('network down'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('an honest empty state when no resolved action has a stakes tier yet', (tester) async {
    const emptyStats = GateStatsData(
      totalResolved: 0,
      stakesCounts: {},
      successCount: 0,
      caughtCount: 0,
      rejectedCount: 0,
      uncertainCount: 0,
      catchRate: null,
      rowsWithRecordedTimeline: 0,
      stageBRanCount: 0,
      revisedCount: 0,
      quotaUsed: null,
      quotaLimit: null,
    );
    await tester.pumpWidget(_harness(
      fetchValidators: () async => _validators,
      fetchStats: () async => emptyStats,
    ));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('Nothing to break down yet'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Nothing to break down yet'), findsOneWidget);
  });
}
