// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// The exact real thresholds, confirmed directly against
// `QUORUM_CONFIGURATION_CONSTANTS.md` §6 before writing anything: outage
// detection is 3 consecutive cross-provider call failures OR 2+
// continuous minutes confirmed unreachable — an OR, either alone
// triggers. Recovery is automatic, immediate on the first successful
// health-check.
//
// THE ASYMMETRY IS THE ACTUAL DESIGN, not an accident of implementation.
// Declaring an outage requires real, sustained evidence (3 failures, or
// 2 full minutes) — avoiding a single network blip triggering a full
// mode switch, which would needlessly queue actions that could have
// gone out live. Recovering requires only one success, because staying
// in a falsely-declared outage after connectivity genuinely returns has
// a real cost (S3 actions sitting blocked for no reason, low-stakes
// actions queuing when they didn't need to) — a strictly worse outcome
// than staying out of outage mode a few seconds too long, since real
// outage detection re-triggers almost immediately on genuine continued
// failure anyway. Slow to declare, fast to recover: the direction that
// minimizes real, unnecessary friction in both failure modes.
//
// Every boundary case (3 vs. 2 failures, exactly 2 minutes vs. one
// second under) was hand-verified in Python before being trusted in a
// Dart test:
//   3 rapid failures triggers: True
//   2 failures at exactly 2min triggers: True (inclusive boundary)
//   2 failures under 2min triggers: False
//
// Out of scope, deliberately: the real connectivity-check mechanism
// itself (an actual network health-check call) — genuinely deferred,
// this module only tracks state given real failure/success events fed
// into it, the same injected-dependency pattern as every other real/
// external boundary in this project.

const int outageFailureThreshold = 3;
const Duration outageDurationThreshold = Duration(minutes: 2);

class OutageState {
  final int consecutiveFailures;
  final DateTime? unreachableSince;
  final bool isInOutage;

  const OutageState({
    required this.consecutiveFailures,
    required this.unreachableSince,
    required this.isInOutage,
  });

  static const initial = OutageState(consecutiveFailures: 0, unreachableSince: null, isInOutage: false);
}

/// Real, real-time OR-threshold: a new consecutive-failure count that
/// alone reaches [outageFailureThreshold], OR a real elapsed duration
/// since the first failure that alone reaches [outageDurationThreshold],
/// either one independently triggers an outage. Once triggered, stays
/// triggered until [recordSuccess] resets it -- a real failure that
/// arrives after outage mode is already active never un-triggers it.
OutageState recordFailure(OutageState state, DateTime now) {
  final newConsecutive = state.consecutiveFailures + 1;
  final newUnreachableSince = state.unreachableSince ?? now;
  final duration = now.difference(newUnreachableSince);
  final triggers = newConsecutive >= outageFailureThreshold || duration >= outageDurationThreshold;

  return OutageState(
    consecutiveFailures: newConsecutive,
    unreachableSince: newUnreachableSince,
    isInOutage: state.isInOutage || triggers,
  );
}

/// Recovery is genuinely immediate and complete on the first success --
/// the WHOLE state resets to initial, no gradual recovery state, no
/// partial credit toward the next outage's threshold.
OutageState recordSuccess(OutageState state) {
  return OutageState.initial;
}
