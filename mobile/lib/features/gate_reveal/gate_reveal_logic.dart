// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// Every schema field checked directly against
// backend/src/quorum_backend/gate/schemas.py before writing a single
// line here, not assumed from memory:
//   evidence_state: Literal["verified_true", "verified_false", "no_data_found"]
//   signed_off: bool = False
// -- confirmed live via direct grep before this file existed.
//
// HONEST DISCREPANCY, disclosed per this project's standing discipline:
// this session's own kickoff prompt described `quorum_theme.dart` as
// already defining three status colors (`verified`, `needsAttention`,
// `uncertain`) with only `critical` missing. In this repository's real,
// current copy of that file (as of the end of MOBILE_07), NONE of the
// four existed -- confirmed by direct grep returning zero results before
// this session began. All four were added together in this session, not
// just the fourth.
//
// THE REAL, LOAD-BEARING DISTINCTION this file exists to preserve: the
// backend's Critic is obligated (see Objection's own real docstring in
// gate/schemas.py) to return either real objections or an explicit
// signed_off=true entry -- NEVER a bare empty list, when it genuinely
// runs. This is what makes stageBRan()'s check below correct FOR THE
// CRITIC SPECIFICALLY: a list containing ONLY a sign-off entry means the
// Critic ran and found nothing to object to.
//
// CRITICAL-tier review correction (DEC-146): that obligation is the
// CRITIC's alone. `gate/orchestration.py::run_stage_b()` only calls the
// real Critic for S3 -- an S2 action reaches the Judge directly with a
// real, empty `objections` list, and the Judge never fabricates a
// sign-off entry on an empty input. So a real, live S2 action that
// genuinely went through Stage B (possibly escalated to a human by the
// Judge itself) can carry an honestly empty `objections` list. Reading
// `objections.isEmpty` as "Stage B never ran" is therefore only correct
// for a caller that already knows this is an S3 action -- the original
// version of this file's `stageBRan(objections)` was wrong for the real,
// reachable S2 case, and `gate_reveal_screen.dart` was changed to use
// `stageBRanForStakes(stakes)` instead, which reads the Gate's own
// structural stakes value (the same hardcoded-lookup discipline
// `router.STAKES_TABLE` already uses) rather than inferring it from
// list emptiness. `stageBRan(objections)` is kept, unchanged and still
// correctly tested, for any future caller that already knows it's
// looking at a real S3 verdict specifically.

enum EvidenceVisualState { positive, negative, uncertain }

/// Maps the real, three-valued `evidence_state` to a visual state --
/// `no_data_found` is NEVER collapsed into a pass or fail; it gets its
/// own genuinely distinct `uncertain` state, matching the backend's own
/// three-valued discipline exactly (gate/schemas.py's Finding docstring:
/// "evidence_state is NEVER binary").
EvidenceVisualState visualStateForEvidence(String evidenceState) {
  switch (evidenceState) {
    case 'verified_true':
      return EvidenceVisualState.positive;
    case 'verified_false':
      return EvidenceVisualState.negative;
    case 'no_data_found':
      return EvidenceVisualState.uncertain;
    default:
      // An unrecognized value is treated the same as genuine uncertainty
      // -- never silently presented as a pass, which would be the more
      // dangerous failure direction.
      return EvidenceVisualState.uncertain;
  }
}

class FindingSummary {
  final String validator;
  final String claim;
  final EvidenceVisualState visualState;

  const FindingSummary({
    required this.validator,
    required this.claim,
    required this.visualState,
  });
}

class ObjectionSummary {
  final String category;
  final String severity;
  final String description;
  final bool signedOff;

  const ObjectionSummary({
    required this.category,
    required this.severity,
    required this.description,
    required this.signedOff,
  });
}

class StageBSummary {
  final List<ObjectionSummary> realObjections;
  final bool signedOff;

  const StageBSummary({
    required this.realObjections,
    required this.signedOff,
  });
}

/// An empty list means Stage B never ran (never called for this action,
/// e.g. an S0/S1 proposal). ANY non-empty list -- including a
/// sign-off-only list -- means Stage B genuinely ran. This is only
/// correct because the real backend guarantees Stage B never returns a
/// bare empty list when it genuinely ran (see file header).
bool stageBRan(List<ObjectionSummary> objections) {
  return objections.isNotEmpty;
}

/// The real, general-purpose check `GateRevealScreen` actually uses
/// (DEC-146) -- Stage B ran if and only if the real Gate's own stakes
/// value is S2 or S3 (`gate/orchestration.py::review()`'s own
/// structural branch), never inferred from whether `objections` happens
/// to be non-empty. See this file's header for why the objections-list
/// check above is real and correctly tested, but only for a caller that
/// already knows it's looking at an S3 verdict specifically.
bool stageBRanForStakes(String stakes) {
  return stakes == 'S2' || stakes == 'S3';
}

/// Separates real objections from sign-off entries. A defensive edge
/// case handled even though the real schema says it shouldn't occur: a
/// mixed list (a real objection alongside a sign-off entry) is still
/// summarized sensibly -- realObjections filters OUT every signed-off
/// entry, and signedOff is true if ANY entry in the list is signed off,
/// regardless of what else is present.
StageBSummary summarizeStageB(List<ObjectionSummary> objections) {
  final realObjections = objections.where((o) => !o.signedOff).toList();
  final signedOff = objections.any((o) => o.signedOff);
  return StageBSummary(realObjections: realObjections, signedOff: signedOff);
}

/// Batch 10 Phase 4 -- a real, disclosed bundling type, the same
/// construction-not-copy pattern this project applies to every schema
/// without a literal source (e.g. `today_screen.dart`'s
/// `TodayScreenData`). No document in this project's spec corpus ever
/// gave "everything one real Gate Reveal navigation needs" a name; this
/// groups `GateRevealScreen`'s own two required constructor params so
/// a single fetcher (`GateRevealFetcher`, `shell/main_shell.dart`) can
/// return both together for a given real proposal.
class GateRevealBundle {
  final String stakes;

  /// `null` means the backend genuinely never recorded this (a real
  /// `action_events` row written before migration `0013`) -- NOT the
  /// same as a real, empty list, which means the Gate ran and recorded
  /// zero findings/objections. A CRITICAL-tier review finding
  /// (`DEC-146`) caught an earlier version of the backend collapsing
  /// this into a fabricated `[]`; this type preserves the real
  /// distinction all the way to the widget that renders it.
  final List<FindingSummary>? findings;
  final List<ObjectionSummary>? objections;

  const GateRevealBundle({required this.stakes, required this.findings, required this.objections});
}
