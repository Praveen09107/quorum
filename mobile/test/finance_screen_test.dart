// Real widget tests for features/finance/finance_screen.dart -- the
// redesign's own new "Finance hub" work (budget bar + recent expenses,
// alongside the existing real subscriptions list).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/features/finance/finance_screen.dart';

Widget _harness({
  List<DetectedSubscriptionData> subscriptions = const [],
  double? monthToDateSpend,
  double? monthlyBudgetLimit,
  List<ExpenseData>? recentExpenses,
}) {
  return MaterialApp(
    home: Scaffold(
      body: FinanceScreen(
        subscriptions: subscriptions,
        monthToDateSpend: monthToDateSpend,
        monthlyBudgetLimit: monthlyBudgetLimit,
        recentExpenses: recentExpenses,
      ),
    ),
  );
}

void main() {
  // `DEC-211` (product rebuild Part C visual pass): section labels now
  // render through `SectionHeader`/`QuorumMono.label`, which uppercase
  // deliberately -- the same real mono-label convention every other
  // redesigned screen in this app already uses (e.g. the Email
  // workspace's "AWAITING REPLY"). The underlying section still exists
  // and still gates on the identical real data; only the literal
  // rendered case of its own label text changed intentionally.
  testWidgets('a real budget bar shows the real spend and limit when both are supplied', (tester) async {
    await tester.pumpWidget(_harness(monthToDateSpend: 1500, monthlyBudgetLimit: 50000));

    expect(find.text('THIS MONTH'), findsOneWidget);
    expect(find.text('₹1500 of ₹50000 spent'), findsOneWidget);
  });

  testWidgets('no real budget bar renders when the data is not supplied', (tester) async {
    await tester.pumpWidget(_harness());

    expect(find.text('THIS MONTH'), findsNothing);
  });

  testWidgets('a real recent-expenses section shows every real expense', (tester) async {
    await tester.pumpWidget(_harness(recentExpenses: [
      ExpenseData(expenseId: 'e1', payee: 'A real coffee shop', amount: 250, occurredAt: DateTime(2026, 9, 28)),
    ]));

    expect(find.text('RECENT EXPENSES'), findsOneWidget);
    expect(find.text('A real coffee shop'), findsOneWidget);
    expect(find.text('₹250'), findsOneWidget);
  });

  testWidgets('no real recent-expenses section renders when the list is empty or not supplied', (tester) async {
    await tester.pumpWidget(_harness());

    expect(find.text('RECENT EXPENSES'), findsNothing);
  });

  testWidgets('the existing real subscriptions section still renders correctly, now alongside the new sections', (tester) async {
    await tester.pumpWidget(_harness(
      subscriptions: const [
        DetectedSubscriptionData(payee: 'A real streaming service', averageAmount: 499, occurrences: 4, averageIntervalDays: 30),
      ],
      monthToDateSpend: 1500,
      monthlyBudgetLimit: 50000,
      recentExpenses: [
        ExpenseData(expenseId: 'e1', payee: 'A real coffee shop', amount: 250, occurredAt: DateTime(2026, 9, 28)),
      ],
    ));

    expect(find.text('SUBSCRIPTIONS'), findsOneWidget);
    expect(find.text('A real streaming service'), findsOneWidget);
    // All three real sections coexist in the same real hub.
    expect(find.text('THIS MONTH'), findsOneWidget);
    expect(find.text('RECENT EXPENSES'), findsOneWidget);
  });

  testWidgets('a genuinely empty screen still shows the real honest "no subscriptions" message', (tester) async {
    await tester.pumpWidget(_harness());

    expect(find.text('No recurring subscriptions detected.'), findsOneWidget);
  });
}
