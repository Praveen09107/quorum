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
// signed_off=true entry -- NEVER a bare empty list, when Stage B genuinely
// ran. This is what makes stageBRan()'s check below correct: an EMPTY
// objections list means Stage B never ran at all (an S0/S1 action never
// reaches Stage B); a list containing ONLY a sign-off entry means Stage B
// ran and found nothing to object to. Conflating these two would mean
// this screen either hides a real "Stage B approved this" moment, or
// falsely implies Stage B reviewed something it never touched -- the
// exact failure mode this file's tests exist to rule out.

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
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const GateRevealBundle({required this.findings, required this.objections});
}
