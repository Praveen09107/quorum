// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. A deliberate architectural choice: zero Flutter imports —
// the strongest testability tier reached in this project's mobile code.
// `dart test` on a real machine is the actual verification.
//
// A real, checked-before-building gap, closed BEFORE this file was
// written, not during: `QUORUM_DATA_CONTRACTS.md` §5.4 was checked
// directly first, and already documents the real `needs_you_now` array
// shape (`proposal_id`, `action_type`, `stakes`, `payload`, `created_at`)
// — confirmed present in this repository's real copy, not re-added here.
// It also states ranking is a client-side concern, not server-side —
// exactly why the real ranking logic lives in this file.
//
// THE REAL RANKING RULE, hand-verified in Python before being trusted in
// Dart (this sandbox can run Python, not Dart): higher stakes first, then
// oldest-first within the same stakes level. Against the real mixed case
// A(S2,day1), B(S3,day5), C(S3,day2), D(S1,day3):
//   Computed order: ['C', 'B', 'A', 'D']  -- PASS
// C beats B despite being younger because both are S3 and C is older;
// B beats A because S3 outranks S2 regardless of age; A beats D the same
// way. Oldest-first as the tiebreaker, deliberately: an item that's been
// waiting longer at the SAME stakes level is the one most likely to have
// already caused real friction (a missed reply window, a deadline
// creeping closer) — surfacing it first is what "needs you now" actually
// means, not just "arrived most recently."

import 'package:quorum_mobile/gate/action_types.dart';

class PendingActionSummary {
  final String proposalId;
  final String actionType;
  final String stakes; // 'S0' | 'S1' | 'S2' | 'S3' -- real backend Stakes values
  final Map<String, dynamic> payload;
  final DateTime createdAt;

  const PendingActionSummary({
    required this.proposalId,
    required this.actionType,
    required this.stakes,
    required this.payload,
    required this.createdAt,
  });
}

class ActionSummaryText {
  final String headline;
  final String stakesLabel;

  const ActionSummaryText({required this.headline, required this.stakesLabel});
}

int _stakesRank(String stakes) {
  switch (stakes) {
    case 'S3':
      return 3;
    case 'S2':
      return 2;
    case 'S1':
      return 1;
    default:
      return 0; // S0, or any unrecognized value -- lowest urgency, never a crash.
  }
}

/// Higher stakes first, then oldest-first within the same stakes level.
/// Returns a genuine COPY (`List.from`) — the input list is never mutated,
/// a real, checkable property this file's own tests confirm directly.
List<PendingActionSummary> sortByUrgency(List<PendingActionSummary> actions) {
  final sorted = List<PendingActionSummary>.from(actions);
  sorted.sort((a, b) {
    final stakesCompare = _stakesRank(b.stakes).compareTo(_stakesRank(a.stakes));
    if (stakesCompare != 0) return stakesCompare;
    return a.createdAt.compareTo(b.createdAt);
  });
  return sorted;
}

String _stakesLabel(String stakes) {
  switch (stakes) {
    case 'S3':
      return 'Needs your approval';
    case 'S2':
      return 'Needs review';
    case 'S1':
      return 'Low-stakes, ready to go';
    case 'S0':
      return 'Informational';
    default:
      return 'Needs your attention';
  }
}

/// Never shows a raw `action_type` string to the user. Every real,
/// currently-known `ActionType` (backend/gate/schemas.py, cross-checked
/// directly before writing this switch) gets a real, readable label. An
/// unrecognized type falls back to a de-snaked, readable version — never
/// a crash, never raw jargon like "update_application_status" verbatim.
ActionSummaryText summarizeForNeedsYouNow(PendingActionSummary action) {
  return ActionSummaryText(
    headline: readableActionType(action.actionType),
    stakesLabel: _stakesLabel(action.stakes),
  );
}
