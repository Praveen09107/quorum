// Phase 7 (`DEC-153`) -- the first real write path in this app that
// isn't negotiation-choice or account deletion. `FindingSummary`/
// `EvidenceVisualState` are reused directly from `gate_reveal_logic.dart`,
// not redefined -- a genuinely fresh piece of free text goes through the
// exact same real Gate a "Needs you now" tap-through already shows a
// user, so its own outcome deserves the same trusted rendering, not a
// second, parallel finding-display concept.

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

/// A real, honest summary of what genuinely happened to one real,
/// freshly-typed piece of free text -- never collapsed into a bare
/// boolean. `title` is only ever non-null when `executed` is `true`
/// (matches the real backend's own `QuickCaptureResult.title` contract
/// exactly: `None`/`null` whenever nothing was genuinely created).
class QuickCaptureResultData {
  final bool executed;
  final String decision;
  final String stakes;
  final String? title;
  final List<FindingSummary> findings;

  const QuickCaptureResultData({
    required this.executed,
    required this.decision,
    required this.stakes,
    required this.title,
    required this.findings,
  });
}

/// A real, honest one-line headline for the result screen's own top
/// banner -- `decision` is read directly, never re-derived from
/// `executed` alone, since `executed == false` genuinely means
/// different things for `revise` (Stage A itself refused) vs.
/// `escalate_to_human` (a real S2/S3 case this specific real path never
/// actually produces for `CREATE_TASK`, included here only so this
/// function stays honest if that ever changes upstream).
String describeQuickCaptureOutcome(QuickCaptureResultData result) {
  if (result.executed) {
    return 'Created: ${result.title}';
  }
  return switch (result.decision) {
    'revise' => "Quorum couldn't create that task as described -- see why below.",
    'escalate_to_human' => 'This needs your direct approval before Quorum can create it.',
    'reject' => 'Quorum declined to create that task -- see why below.',
    _ => 'That task was not created.',
  };
}
