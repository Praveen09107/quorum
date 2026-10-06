// Real tests for features/today/week_summary_logic.dart. Zero Flutter
// dependencies — plain Dart, `dart test` is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/today/week_summary_logic.dart';

WeekSummaryData _data({
  int tasksDueThisWeek = 0,
  double monthToDateSpend = 0,
  double monthlyBudgetLimit = 50000,
  int applicationsInProgress = 0,
  int waitingOnCount = 0,
}) {
  return WeekSummaryData(
    tasksDueThisWeek: tasksDueThisWeek,
    monthToDateSpend: monthToDateSpend,
    monthlyBudgetLimit: monthlyBudgetLimit,
    applicationsInProgress: applicationsInProgress,
    waitingOnCount: waitingOnCount,
  );
}

void main() {
  group('formatSpendSummary', () {
    test('a real, normal spend/limit pair formats as "of"', () {
      expect(formatSpendSummary(_data(monthToDateSpend: 250, monthlyBudgetLimit: 50000)), '₹250 of ₹50000');
    });

    test('a real, defensive zero limit falls back to spend alone, never divides by zero', () {
      expect(formatSpendSummary(_data(monthToDateSpend: 250, monthlyBudgetLimit: 0)), '₹250 spent this month');
    });
  });

  group('formatTasksDueSummary -- real pluralization', () {
    test('zero tasks due', () {
      expect(formatTasksDueSummary(0), '0 tasks due this week');
    });

    test('exactly one task due uses the real singular form', () {
      expect(formatTasksDueSummary(1), '1 task due this week');
    });

    test('multiple tasks due uses the real plural form', () {
      expect(formatTasksDueSummary(3), '3 tasks due this week');
    });
  });

  group('formatApplicationsSummary -- real pluralization', () {
    test('exactly one application uses the real singular form', () {
      expect(formatApplicationsSummary(1), '1 application in progress');
    });

    test('multiple applications uses the real plural form', () {
      expect(formatApplicationsSummary(2), '2 applications in progress');
    });
  });

  group('formatWaitingOnSummary', () {
    test('zero gets a real, honest, positive message -- not "0 waiting"', () {
      expect(formatWaitingOnSummary(0), 'Nothing waiting on a reply');
    });

    test('exactly one uses the real singular form', () {
      expect(formatWaitingOnSummary(1), '1 waiting on a reply');
    });

    test('multiple uses the real plural form', () {
      expect(formatWaitingOnSummary(4), '4 waiting on a reply');
    });
  });
}
