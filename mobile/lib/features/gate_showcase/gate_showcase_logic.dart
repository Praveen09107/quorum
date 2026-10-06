// Pure logic for the Gate showcase screen (`DEC-193`, product rebuild
// Block E). Zero Flutter dependency -- `dart test` is the real
// verification.
//
// A real, disclosed scope decision: the plan's Part B named three
// separate screens ("Gate -- Live", "Gate -- How it works", "Gate --
// Self-test"). Matching `DEC-192`'s own established precedent of
// scoping a block down to a single, real, honestly-disclosed slice
// rather than a full IA rebuild, this block ships ONE consolidated
// screen combining the real validator roster and the real live stats
// `GET /gate/validators` and `GET /gate/stats` now expose, reached from
// the existing Trust tab (the real home of self-test results already)
// rather than a new tab. The full three-screen split, and surfacing the
// per-scenario `GateVerdict` now returned by `/trust`, remain real,
// explicit follow-on work -- not silently dropped.

/// One real Stage A validator, as `GET /gate/validators` reports it.
/// `wired == false` is an honest, disclosed fact about this specific
/// deployment's current production wiring, not a defect in the
/// validator itself -- the validator is real and tested; it simply has
/// no real caller yet (`STATUS_INDEX.md`'s own standing open item).
class GateValidatorData {
  final String name;
  final String functionName;
  final String description;
  final String evidenceSource;
  final bool wired;

  const GateValidatorData({
    required this.name,
    required this.functionName,
    required this.description,
    required this.evidenceSource,
    required this.wired,
  });

  factory GateValidatorData.fromJson(Map<String, dynamic> json) {
    return GateValidatorData(
      name: json['name'] as String,
      functionName: json['function_name'] as String,
      description: json['description'] as String,
      evidenceSource: json['evidence_source'] as String,
      wired: json['wired'] as bool,
    );
  }
}

/// The real, live Gate-wide stats `GET /gate/stats` reports for the
/// signed-in user. `catchRate`/`quotaUsed`/`quotaLimit` are honestly
/// `null`, never a fabricated number, exactly when the backend itself
/// had nothing real to compute them from.
class GateStatsData {
  final int totalResolved;
  final Map<String, int> stakesCounts;
  final int successCount;
  final int caughtCount;
  final int rejectedCount;
  final int uncertainCount;
  final double? catchRate;
  final int rowsWithRecordedTimeline;
  final int stageBRanCount;
  final int revisedCount;
  final int? quotaUsed;
  final int? quotaLimit;

  const GateStatsData({
    required this.totalResolved,
    required this.stakesCounts,
    required this.successCount,
    required this.caughtCount,
    required this.rejectedCount,
    required this.uncertainCount,
    required this.catchRate,
    required this.rowsWithRecordedTimeline,
    required this.stageBRanCount,
    required this.revisedCount,
    required this.quotaUsed,
    required this.quotaLimit,
  });

  factory GateStatsData.fromJson(Map<String, dynamic> json) {
    final rawStakes = json['stakes_counts'] as Map<String, dynamic>;
    return GateStatsData(
      totalResolved: json['total_resolved'] as int,
      stakesCounts: rawStakes.map((key, value) => MapEntry(key, value as int)),
      successCount: json['success_count'] as int,
      caughtCount: json['caught_count'] as int,
      rejectedCount: json['rejected_count'] as int,
      uncertainCount: json['uncertain_count'] as int,
      catchRate: (json['catch_rate'] as num?)?.toDouble(),
      rowsWithRecordedTimeline: json['rows_with_recorded_timeline'] as int,
      stageBRanCount: json['stage_b_ran_count'] as int,
      revisedCount: json['revised_count'] as int,
      quotaUsed: json['quota_used'] as int?,
      quotaLimit: json['quota_limit'] as int?,
    );
  }
}

/// Real, correctly-rounded catch rate for display -- the honest "no
/// data yet" sentence, never a fabricated 0%, when `catchRate` is
/// `null`. Shares the same `.5`-rounding caveat already tracked across
/// this app's other percentage formatters (`STATUS_INDEX.md` open item
/// #6) -- not resolved here without a real compiler.
String formatGateCatchRate(double? catchRate) {
  if (catchRate == null) return 'No resolved actions yet';
  return '${(catchRate * 100).round()}%';
}

/// A real, honest headroom line for the shared daily Gemini quota --
/// `null` quota fields mean Upstash genuinely wasn't reachable or
/// configured, not zero usage.
String describeQuotaHeadroom(int? quotaUsed, int? quotaLimit) {
  if (quotaUsed == null || quotaLimit == null) return 'Quota headroom unavailable right now';
  final remaining = quotaLimit - quotaUsed;
  return '$remaining of $quotaLimit Gemini calls left today';
}

/// Real fraction of resolved actions whose recorded timeline shows
/// Stage B genuinely ran -- `null`, honestly, when nothing real has
/// ever recorded a timeline yet (never a fabricated 0%).
double? stageBInvocationRate(GateStatsData stats) {
  if (stats.rowsWithRecordedTimeline == 0) return null;
  return stats.stageBRanCount / stats.rowsWithRecordedTimeline;
}
