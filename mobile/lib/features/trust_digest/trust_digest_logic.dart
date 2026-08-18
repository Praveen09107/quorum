// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// Confirmed already correct in this repository's real copy of
// `QUORUM_DATA_CONTRACTS.md` §5.15 before writing this file: the
// `/trust_digest` JSON shape (`current_week`, `previous_week`, `trend`,
// `delta`) is already documented — no edit needed.
//
// This session's real backend counterpart, `backend/src/quorum_backend/
// features/trust_digest.py`, is a genuinely NEW backend module, not just
// a missing endpoint — built in this same session (see `DEC-089`),
// following `WeeklyTrustSummary`/`TrendResult`'s field names exactly.
//
// THE SAME FAIL-CLOSED PRINCIPLE AS `MOBILE_16`'s `parseTarget`,
// reapplied without needing to be re-derived: `parseTrend` fails to
// `insufficientData` on any unrecognized value, never to `stable` --
// `stable` would falsely claim a real week-over-week comparison was
// made when it genuinely wasn't.

enum TrustTrend { improving, declining, stable, insufficientData }

class WeeklyTrustSummaryData {
  final String weekStart;
  final int totalActions;
  final double successRate;

  const WeeklyTrustSummaryData({
    required this.weekStart,
    required this.totalActions,
    required this.successRate,
  });
}

class TrustDigestData {
  final WeeklyTrustSummaryData currentWeek;
  final WeeklyTrustSummaryData? previousWeek;
  final TrustTrend trend;
  final double? delta;

  const TrustDigestData({
    required this.currentWeek,
    required this.previousWeek,
    required this.trend,
    required this.delta,
  });
}

/// Fails CLOSED to insufficientData -- the real, honest state for "we
/// couldn't make a real comparison at all," never silently reported as
/// "stable," which would claim a real comparison WAS made and found no
/// change. These are genuinely different real claims.
TrustTrend parseTrend(String raw) {
  switch (raw) {
    case 'improving':
      return TrustTrend.improving;
    case 'declining':
      return TrustTrend.declining;
    case 'stable':
      return TrustTrend.stable;
    default:
      return TrustTrend.insufficientData;
  }
}

String trendLabel(TrustTrend trend) {
  switch (trend) {
    case TrustTrend.improving:
      return 'Improving';
    case TrustTrend.declining:
      return 'Declining';
    case TrustTrend.stable:
      return 'Holding steady';
    case TrustTrend.insufficientData:
      return 'Not enough data yet to compare';
  }
}

/// Real, signed percentage-point formatting. A null delta (the real
/// insufficient_data case) renders as an empty string -- never a
/// misleading placeholder number like "0 pts", which would falsely
/// imply a real, computed zero change. A negative delta shows its own
/// native minus sign exactly once -- never double-signed as "+-3".
String formatDelta(double? delta) {
  if (delta == null) return '';
  final points = (delta * 100).round();
  final sign = points > 0 ? '+' : '';
  return '$sign$points pts';
}
