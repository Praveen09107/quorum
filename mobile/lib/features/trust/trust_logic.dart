// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// A real gap, confirmed already fixed in this repository's real copy of
// `QUORUM_DATA_CONTRACTS.md` §5.14 before writing this file — the
// `target: "stub" | "real_gate"` field is already documented there, not
// re-added here.
//
// A SIGNIFICANT, DISCLOSED DISCREPANCY, per this project's standing
// discipline: this session's own kickoff prompt describes a real backend
// fix as already necessary and in-scope -- correcting a stale docstring
// claim in `backend/features/self_test_harness.py` (which allegedly
// said the real Gate "doesn't exist yet as code") and adding a real
// `target` field to `run_self_test()`. **`backend/features/self_test_
// harness.py` does not exist anywhere in this repository** -- confirmed
// live by direct search, consistent with `STATUS_INDEX.md`'s standing
// disclosure that `backend/features/*` (the ADD §9.7 "newly built
// features" table, including the Self-Test Harness) has never been
// built in this repository's real history. There is no stale docstring
// to correct in a file that was never written here, and no backend
// change is made in this session as a result -- fabricating one against
// a nonexistent file would be exactly the kind of invented-work this
// project's discipline exists to prevent. This mobile screen is built
// entirely against §5.14's real, already-correct JSON contract, which
// conveniently already specifies the real `target` field regardless.
//
// THE REAL, LOAD-BEARING HONESTY REQUIREMENT preserved regardless: a
// caller displaying trust data without checking `target` first would
// present stub-gate results as if they measured the real Gate -- a
// genuine misrepresentation. `parseTarget` fails CLOSED to `stub` on any
// unrecognized value -- the cautious, honest direction. Failing the
// other way (defaulting to `realGate`) would overstate confidence in a
// measurement that was never actually confirmed to be real.

enum SelfTestTarget { stub, realGate }

class ScenarioResultData {
  final String scenarioId;
  final String expected;
  final String actual;
  final bool passed;

  const ScenarioResultData({
    required this.scenarioId,
    required this.expected,
    required this.actual,
    required this.passed,
  });
}

class TrustData {
  final int total;
  final int caught;
  final List<ScenarioResultData> missed;
  final List<ScenarioResultData> results;
  final SelfTestTarget target;

  const TrustData({
    required this.total,
    required this.caught,
    required this.missed,
    required this.results,
    required this.target,
  });
}

/// Fails CLOSED to stub -- the honest, cautious direction. Never
/// silently claims realGate on a value this app doesn't recognize.
SelfTestTarget parseTarget(String raw) {
  return raw == 'real_gate' ? SelfTestTarget.realGate : SelfTestTarget.stub;
}

/// Makes the stub-vs-real distinction impossible to miss -- a self-test
/// result against the stub gate is a real, useful signal that the
/// harness itself works, but it is NOT a real measurement of the actual
/// Gate's adversarial performance.
String targetLabel(SelfTestTarget target) {
  switch (target) {
    case SelfTestTarget.stub:
      return 'Testing against a demo Gate, not the real one yet';
    case SelfTestTarget.realGate:
      return 'Testing against the real Gate';
  }
}

/// Real, correctly-rounded catch rate. Part of the same tracked Dart
/// `.5`-rounding uncertainty shared across five real files this batch
/// (STATUS_INDEX.md open item #6) -- never resolved here without a real
/// compiler.
String formatCatchRate(int caught, int total) {
  if (total == 0) return 'No data yet';
  return '${(caught / total * 100).round()}%';
}
