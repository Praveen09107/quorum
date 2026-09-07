// Phase 7 (`DEC-153`) -- the first real write path in this app that
// isn't negotiation-choice or account deletion. `FindingSummary`/
// `EvidenceVisualState` are reused directly from `gate_reveal_logic.dart`,
// not redefined -- a genuinely fresh piece of free text goes through the
// exact same real Gate a "Needs you now" tap-through already shows a
// user, so its own outcome deserves the same trusted rendering, not a
// second, parallel finding-display concept.
//
// REAL, DISCLOSED SESSION-4 EXTENSION (`QUORUM_FINAL_COMPLETION_PLAN.md`):
// this file's own real backend contract (`POST /quick_capture`) now
// covers a second real domain, Finance -- `domain` is always present;
// `amount`/`category`/`financeAction` are the real Finance-domain
// equivalent of `title`, populated only when `domain == 'finance'` and
// `executed == true`. `formatCurrency` is reused directly from
// `finance_logic.dart` (not redefined) -- the same real `₹` display
// convention the Finance/Subscriptions screens already use.

import 'package:quorum_mobile/features/finance/finance_logic.dart' show formatCurrency;
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

/// A real, honest summary of what genuinely happened to one real,
/// freshly-typed piece of free text -- never collapsed into a bare
/// boolean. `title` is only ever non-null when `domain == 'tasks'` AND
/// `executed` is `true` (matches the real backend's own `QuickCapture
/// Result.title` contract exactly: `None`/`null` whenever nothing was
/// genuinely created, or the domain isn't `tasks`). `amount`/`category`/
/// `financeAction` are the real `finance`-domain equivalent, under the
/// identical "only non-null on a genuine, matching-domain execute" rule.
class QuickCaptureResultData {
  final bool executed;
  final String decision;
  final String stakes;
  final String domain;
  final String? title;
  final double? amount;
  final String? category;
  final String? financeAction;
  final List<FindingSummary> findings;

  const QuickCaptureResultData({
    required this.executed,
    required this.decision,
    required this.stakes,
    required this.domain,
    required this.title,
    this.amount,
    this.category,
    this.financeAction,
    required this.findings,
  });
}

/// A real, honest one-line headline for the result screen's own top
/// banner -- `decision` is read directly, never re-derived from
/// `executed` alone, since `executed == false` genuinely means
/// different things for `revise` (Stage A itself refused) vs.
/// `escalate_to_human` (a real case `LOG_EXPENSE`/`CREATE_TASK` never
/// produce, S1 both, but `UPDATE_BUDGET` -- real `S2` -- genuinely can).
///
/// REAL, DISCLOSED SESSION-4 EXTENSION: the genuine-approve case now
/// branches on `result.domain` -- a real `finance` result never had a
/// real `title` to show (it's a `tasks`-only field), so this never
/// falls through to a bare "Created: null".
String describeQuickCaptureOutcome(QuickCaptureResultData result) {
  if (result.executed) {
    if (result.domain == 'finance') {
      final amount = result.amount;
      final formattedAmount = amount == null ? 'an amount' : formatCurrency(amount);
      return switch (result.financeAction) {
        'log_expense' => 'Logged: $formattedAmount -- ${result.category ?? 'uncategorized'}',
        'update_budget' => 'Budget updated to $formattedAmount',
        _ => 'Recorded a real finance change.', // defensive -- never genuinely reached today
      };
    }
    return 'Created: ${result.title}';
  }
  return switch (result.decision) {
    'revise' => "Quorum couldn't create that as described -- see why below.",
    'escalate_to_human' => 'This needs your direct approval before Quorum can create it.',
    'reject' => 'Quorum declined to create that -- see why below.',
    _ => 'That was not created.',
  };
}
