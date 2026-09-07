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
//
// REAL, DISCLOSED SESSION-5 EXTENSION: a third real domain, Calendar --
// `eventStart`/`eventEnd`/`eventTitle` follow `title`/`amount`/
// `category`'s own "only when genuinely executed" rule, but
// `calendarAction` deliberately does NOT (see `QuickCaptureResultData`'s
// own docstring below for why this domain's own convention differs).

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
  final String? eventStart;
  final String? eventEnd;
  final String? eventTitle;
  final String? calendarAction;
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
    this.eventStart,
    this.eventEnd,
    this.eventTitle,
    this.calendarAction,
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
    if (result.domain == 'calendar') {
      // Defensive, future-proof (`QUORUM_FINAL_COMPLETION_PLAN.md`
      // Session 5) -- no real path produces `executed: true` for
      // calendar today (see the `decision == 'approve'` branch below
      // for the real, disclosed reason), but this stays honest if a
      // future session ever wires up a real execution target.
      return 'Created: ${result.eventTitle}';
    }
    return 'Created: ${result.title}';
  }
  // RESOLVED, a real, disclosed CRITICAL-tier review LOW: `escalate_to_
  // human` is genuinely reachable for a real `finance` result (`UPDATE_
  // BUDGET` is real `Stakes.S2`, unlike `CREATE_TASK`/`LOG_EXPENSE`,
  // both `S1` -- this is the one real case this switch's own comment
  // below used to dismiss as unreachable). "create it" is real, honest
  // wording for a `tasks` result but wrong for a budget change -- fixed
  // with a domain-aware message. A real, disclosed, accepted limitation,
  // not fixed here: no real "a human approved this escalated action"
  // endpoint exists anywhere in this backend yet (`action_executor.py`'s
  // own docstring says so explicitly) -- a genuinely escalated real
  // `UPDATE_BUDGET` surfaces honestly on `/today`'s Needs You Now zone,
  // but has no real in-app way to be approved from there today.
  if (result.domain == 'finance' && result.decision == 'escalate_to_human') {
    return 'This needs your direct approval before Quorum can change it.';
  }
  // REAL, DISCLOSED SESSION-5 ADDITION: a genuine Gate `approve` that
  // still never executed is the ORDINARY real outcome for `calendar`
  // today, not a rare exception -- neither real calendar action type
  // has a real, live execution path through this route (`QUORUM_DATA_
  // CONTRACTS.md` §5.18 has the full, disclosed reasoning: no real,
  // server-side local execution target exists anywhere in this
  // backend, and a real external Google Calendar booking always needs
  // a real, separate, explicit human approval this route can never
  // itself provide, per `CLAUDE.md`'s own absolute S3 rule). Handled
  // here, before the generic decision switch below, which has no real
  // `'approve'` case of its own and would otherwise fall through to
  // the same uninformative "That was not created" every genuine Stage
  // A/B refusal already gets -- misleadingly implying the Gate
  // declined it, when it genuinely didn't.
  if (result.decision == 'approve') {
    if (result.domain == 'calendar') {
      return switch (result.calendarAction) {
        'create_calendar_event_external' => 'This needs your direct approval before Quorum can send that invite.',
        'create_calendar_event_local' => "Approved -- add this to your calendar for now; direct creation isn't wired up yet.",
        _ => 'Approved, but nothing was written yet.', // defensive -- never genuinely reached today
      };
    }
    return 'Approved, but nothing was written yet.'; // defensive -- a genuine approve should already have executed for every other real domain today
  }
  return switch (result.decision) {
    'revise' => "Quorum couldn't create that as described -- see why below.",
    'escalate_to_human' => 'This needs your direct approval before Quorum can create it.',
    'reject' => 'Quorum declined to create that -- see why below.',
    _ => 'That was not created.',
  };
}
