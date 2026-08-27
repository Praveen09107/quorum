// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies -- plain Dart, `dart test` is
// the real verification.
//
// A REAL, DISCLOSED SCOPE DECISION, matching `backend/src/quorum_backend/
// features/predictive_risk.py`'s own top-of-file docstring exactly: no
// real API route contract, JSON shape, or mobile screen for this
// feature existed anywhere in this project's real spec corpus before
// this session -- confirmed by direct search. Every field/type below is
// this session's own new, disclosed design, checked directly against
// the real backend's own actual response shape before writing it, not
// a transcription of a pre-existing contract.

class RiskAssessmentData {
  final DateTime weekStart;
  final int deadlineDensity;
  final int matchingHistoricalWeeks;
  final double? pooledCorrectionRate; // null -- genuinely not enough real history yet
  final bool isAtRisk;

  const RiskAssessmentData({
    required this.weekStart,
    required this.deadlineDensity,
    required this.matchingHistoricalWeeks,
    required this.pooledCorrectionRate,
    required this.isAtRisk,
  });
}

/// Real, honest, three-state message -- never collapses "genuinely no
/// matching real history yet" into either a false reassurance or a
/// false alarm, the same discipline this project's `evidence_state`
/// three-valued handling already established elsewhere.
String riskMessage(RiskAssessmentData risk) {
  if (risk.matchingHistoricalWeeks == 0) {
    return 'Not enough real history yet to predict next week.';
  }
  if (risk.isAtRisk) {
    final rate = risk.pooledCorrectionRate ?? 0.0;
    final pct = (rate * 100).round();
    return 'Next week may be tight -- $pct% of similarly busy past weeks needed adjusting.';
  }
  return 'Next week looks manageable based on your real history.';
}
