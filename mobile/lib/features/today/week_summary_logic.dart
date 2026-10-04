// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// REAL, NEW (the redesign's own real Today-screen work) -- the real,
// previously-missing "This week across your agents" cross-domain strip
// the approved redesign plan named: "one glanceable row surfacing real,
// live cross-domain numbers already computed by the backend." Backs
// `GET /today/summary` (`features/week_summary.py`).

class WeekSummaryData {
  final int tasksDueThisWeek;
  final double monthToDateSpend;
  final double monthlyBudgetLimit;
  final int applicationsInProgress;
  final int waitingOnCount;

  const WeekSummaryData({
    required this.tasksDueThisWeek,
    required this.monthToDateSpend,
    required this.monthlyBudgetLimit,
    required this.applicationsInProgress,
    required this.waitingOnCount,
  });
}

/// Pure, real formatting -- "₹250 of ₹50,000 spent this month". A real,
/// defensive `monthlyBudgetLimit <= 0` (should never happen against the
/// real backend, which always has a real, positive default) falls back
/// to showing the raw spend alone rather than dividing by zero.
String formatSpendSummary(WeekSummaryData data) {
  final spend = data.monthToDateSpend.round();
  if (data.monthlyBudgetLimit <= 0) {
    return '₹$spend spent this month';
  }
  final limit = data.monthlyBudgetLimit.round();
  return '₹$spend of ₹$limit';
}

/// Pure, real pluralization -- "1 task due this week" vs "3 tasks due
/// this week", never an awkward "1 tasks."
String formatTasksDueSummary(int count) {
  return count == 1 ? '1 task due this week' : '$count tasks due this week';
}

String formatApplicationsSummary(int count) {
  return count == 1 ? '1 application in progress' : '$count applications in progress';
}

String formatWaitingOnSummary(int count) {
  if (count == 0) return 'Nothing waiting on a reply';
  return count == 1 ? '1 waiting on a reply' : '$count waiting on a reply';
}
