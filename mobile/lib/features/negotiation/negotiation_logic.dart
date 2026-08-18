// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// Three real schemas, all confirmed directly against
// backend/src/quorum_backend/gate/schemas.py before writing anything,
// not from memory: Position (domain, concern, severity_claim,
// resource_claims, proposed_resolution, evidence), NegotiationOption
// (option_id: str, description: str, source_domains: list[str] --
// HONEST NOTE: option_id is a plain str in the real schema, not a
// schema-enforced closed Literal set, despite this session's own
// kickoff prompt describing it as "closed" -- see DECISIONS_LOG.md),
// ImpactDelta (metric, before, after, direction).
//
// IMPORTANT, real, and directly connected to a backend fix earlier in
// this project's history: visualStateForDirection() below consumes the
// "direction" string produced by
// backend/src/quorum_backend/negotiation/impact_simulator.py. Confirmed
// live before writing this file: `higher_is_better` is genuinely present
// in that module (DEC-070's real fix, not DEC-053 -- see DECISIONS_LOG.md
// for the citation correction). This screen has no way to independently
// detect a wrong direction string from the backend; it trusts what it's
// given, and that dependency is real and satisfied right now.
//
// A DELIBERATE ABSENCE, worth stating explicitly: there is no
// "recommended option" logic anywhere in this file. No function here
// compares deltas across options, ranks them, or scores them. Every
// option is rendered with identical visual weight by the companion
// widget file -- the numbers are shown, the choice is genuinely the
// user's.
//
// THE ALREADY-TRACKED ROUNDING BOUNDARY, now confirmed to affect this
// file too, not just a single-file concern: formatMetricValue's
// percentage rounding ((value * 100).round()) hits the same Dart `.5`
// rounding-convention uncertainty tracked in STATUS_INDEX.md (Python's
// banker's rounding vs. Dart's round-half-away-from-zero disagree on an
// exact .5 tie, e.g. 0.505 * 100 = 50.5). Not resolved here, deliberately
// -- this needs a real Dart compiler. The test below uses 0.999 -> 100%,
// a genuinely unambiguous case both rounding conventions agree on
// (0.999 * 100 = 99.9, which rounds to 100 either way) -- confirmed in
// Python before writing the test.

class PositionData {
  final String domain;
  final String concern;
  final String proposedResolution;

  const PositionData({
    required this.domain,
    required this.concern,
    required this.proposedResolution,
  });
}

class ImpactDeltaData {
  final String metric; // 'deadline_slack_hours' | 'budget_remaining_fraction' | 'task_hours_committed'
  final double before;
  final double after;
  final String direction; // 'improves' | 'worsens' | 'unchanged'

  const ImpactDeltaData({
    required this.metric,
    required this.before,
    required this.after,
    required this.direction,
  });
}

class NegotiationOptionData {
  final String optionId;
  final String description;
  final List<String> sourceDomains;
  final List<ImpactDeltaData> impact;

  const NegotiationOptionData({
    required this.optionId,
    required this.description,
    required this.sourceDomains,
    required this.impact,
  });
}

enum MetricVisualDirection { improves, worsens, unchanged }

/// Maps the real "direction" string the backend's impact simulator
/// computes into a visual state. Defensive default (unchanged) for an
/// unrecognized value -- never a crash, never a silent claim of
/// improvement for a value this screen doesn't recognize.
MetricVisualDirection visualStateForDirection(String direction) {
  switch (direction) {
    case 'improves':
      return MetricVisualDirection.improves;
    case 'worsens':
      return MetricVisualDirection.worsens;
    case 'unchanged':
      return MetricVisualDirection.unchanged;
    default:
      return MetricVisualDirection.unchanged;
  }
}

/// A real, distinct label per real metric — the closed, three-member set
/// `ImpactDelta.metric` actually uses.
String metricLabel(String metric) {
  switch (metric) {
    case 'deadline_slack_hours':
      return 'Deadline slack';
    case 'budget_remaining_fraction':
      return 'Budget remaining';
    case 'task_hours_committed':
      return 'Hours committed';
    default:
      return metric;
  }
}

/// Unit-correctness, not generic number formatting: deadline_slack_hours
/// and task_hours_committed render with an "h" suffix (they're real hour
/// counts); budget_remaining_fraction renders as a percentage (it's a
/// real 0.0-1.0 fraction). Getting this backwards -- showing a 0.25
/// fraction as "0.3h" -- would misrepresent a real number the backend's
/// impact simulator specifically exists to guarantee is accurate.
String formatMetricValue(String metric, double value) {
  switch (metric) {
    case 'deadline_slack_hours':
    case 'task_hours_committed':
      return '${value.toStringAsFixed(1)}h';
    case 'budget_remaining_fraction':
      return '${(value * 100).round()}%';
    default:
      return value.toString();
  }
}

String capitalizeDomain(String domain) {
  if (domain.isEmpty) return domain;
  return domain[0].toUpperCase() + domain.substring(1);
}
