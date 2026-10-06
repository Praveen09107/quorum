// Real widget tests for the new "Set budget" flow (`DEC-200`, product
// rebuild) -- Finance's first real write path. Exercises the real nav
// chain: YouScreen -> Finance preview card -> FinanceLoader -> FAB ->
// the set-budget sheet -> submit -> a real, local budget-ceiling
// update (no second server round trip -- see `FinanceLoaderState`'s
// own docstring for why).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/api/update_budget_api.dart';
import 'package:quorum_mobile/features/today/week_summary_logic.dart';
import 'package:quorum_mobile/features/you/you_logic.dart';
import 'package:quorum_mobile/features/you/you_screen.dart';

Future<DeletionResultData> _unconfiguredDeletion() => throw UnimplementedError();

Future<WeekSummaryData> _fakeWeekSummary() async {
  return const WeekSummaryData(
    tasksDueThisWeek: 0,
    monthToDateSpend: 10000,
    monthlyBudgetLimit: 50000,
    applicationsInProgress: 0,
    waitingOnCount: 0,
  );
}

void main() {
  testWidgets('submitting the set-budget form shows the real, applied new budget and a success snackbar', (tester) async {
    double? capturedAmount;

    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchFinance: () async => const [],
      fetchWeekSummary: _fakeWeekSummary,
      onUpdateBudget: ({required double amount, String? category}) async {
        capturedAmount = amount;
        return const UpdateBudgetResult(executed: true, decision: 'approve', amount: 60000.0);
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();

    expect(find.textContaining('₹50000'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, 'New monthly budget'), '60000');
    await tester.tap(find.text('Update budget'));
    await tester.pumpAndSettle();

    expect(capturedAmount, 60000.0);
    expect(find.textContaining('of ₹60000 spent'), findsOneWidget);
    expect(find.textContaining('Budget updated'), findsOneWidget);
  });

  testWidgets('a real Judge revision is shown honestly -- the applied amount, never the one submitted', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchFinance: () async => const [],
      fetchWeekSummary: _fakeWeekSummary,
      onUpdateBudget: ({required double amount, String? category}) async {
        return const UpdateBudgetResult(executed: true, decision: 'revise', amount: 55000.0);
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'New monthly budget'), '90000');
    await tester.tap(find.text('Update budget'));
    await tester.pumpAndSettle();

    expect(find.textContaining('of ₹55000 spent'), findsOneWidget);
  });

  testWidgets('a real Gate rejection shows an honest decline message, never a fabricated success', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchFinance: () async => const [],
      fetchWeekSummary: _fakeWeekSummary,
      onUpdateBudget: ({required double amount, String? category}) async {
        return const UpdateBudgetResult(executed: false, decision: 'reject');
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'New monthly budget'), '90000');
    await tester.tap(find.text('Update budget'));
    await tester.pumpAndSettle();

    expect(find.textContaining('declined'), findsOneWidget);
    expect(find.textContaining('₹50000'), findsOneWidget);
  });

  testWidgets('a non-numeric or non-positive entry shows a real, honest validation error, never a silent no-op', (tester) async {
    var callCount = 0;
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchFinance: () async => const [],
      fetchWeekSummary: _fakeWeekSummary,
      onUpdateBudget: ({required double amount, String? category}) async {
        callCount++;
        return const UpdateBudgetResult(executed: true, decision: 'approve', amount: 1);
      },
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.edit_outlined));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'New monthly budget'), 'not a number');
    await tester.tap(find.text('Update budget'));
    await tester.pumpAndSettle();

    expect(callCount, 0);
    expect(find.textContaining('Enter a real, positive amount'), findsOneWidget);
  });

  testWidgets('no FAB appears when onUpdateBudget is not configured, matching the honest-gating precedent', (tester) async {
    final screen = YouScreen(
      onConfirmDelete: _unconfiguredDeletion,
      fetchFinance: () async => const [],
      fetchWeekSummary: _fakeWeekSummary,
    );

    await tester.pumpWidget(MaterialApp(home: Scaffold(body: screen)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Finance'));
    await tester.pumpAndSettle();

    expect(find.byType(FloatingActionButton), findsNothing);
  });
}
