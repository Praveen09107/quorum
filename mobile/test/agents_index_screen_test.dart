// Real widget tests for features/agents/agents_index_screen.dart
// (`DEC-192`, product rebuild Block D).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/agents/agents_index_screen.dart';
import 'package:quorum_mobile/features/agents/agents_logic.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

AgentStatsData _stats(String domain, {int lifetimeActions = 0, double? successRate}) {
  return AgentStatsData(
    domain: domain,
    lifetimeActions: lifetimeActions,
    successCount: 0,
    caughtCount: 0,
    rejectedCount: 0,
    uncertainCount: 0,
    successRate: successRate,
    lastActivity: lifetimeActions > 0 ? DateTime.now() : null,
  );
}

Widget _harness(Future<List<AgentStatsData>> Function() fetch) {
  return MaterialApp(theme: buildQuorumDarkTheme(), home: AgentsIndexScreen(fetch: fetch));
}

void main() {
  testWidgets('renders all five real domain agents by name, even with zero activity', (tester) async {
    await tester.pumpWidget(_harness(() async => [
          _stats('email', lifetimeActions: 5, successRate: 0.8),
          _stats('calendar'),
          _stats('tasks'),
          _stats('finance'),
          _stats('career'),
        ]));
    await tester.pumpAndSettle();

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Calendar'), findsOneWidget);
    expect(find.text('Tasks'), findsOneWidget);

    // Five full agent cards don't all fit one test viewport -- scroll
    // the real list to reach the remaining two real agents.
    await tester.scrollUntilVisible(find.text('Finance'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Finance'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Career'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Career'), findsOneWidget);
  });

  testWidgets('shows a real, honest error state on a real fetch failure, not a crash', (tester) async {
    await tester.pumpWidget(_harness(() async => throw Exception('network down')));
    await tester.pumpAndSettle();

    expect(find.textContaining('network down'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('a real agent with an active track record shows its real stats', (tester) async {
    await tester.pumpWidget(_harness(() async => [
          _stats('email', lifetimeActions: 10, successRate: 0.7),
          _stats('calendar'),
          _stats('tasks'),
          _stats('finance'),
          _stats('career'),
        ]));
    await tester.pumpAndSettle();

    expect(find.text('10'), findsOneWidget);
    expect(find.text('70%'), findsOneWidget);
  });
}
