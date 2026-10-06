// Pure logic for the Agents index (`DEC-192`, product rebuild Block D).
// Zero Flutter dependency -- `dart test` is the real verification.

/// One real agent's real, live track record -- parsed straight from
/// `GET /agents`'s own real response shape. Every field here is a real
/// computed fact, never a placeholder: `lifetimeActions == 0` for a
/// genuinely inactive agent is an honest zero, not a loading state.
class AgentStatsData {
  final String domain;
  final int lifetimeActions;
  final int successCount;
  final int caughtCount;
  final int rejectedCount;
  final int uncertainCount;

  /// `null`, honestly, when there is nothing real to compute a rate
  /// from -- never a fabricated `0.0` standing in for "no data yet."
  final double? successRate;

  /// `null` for an agent that has never had a real resolved action.
  final DateTime? lastActivity;

  const AgentStatsData({
    required this.domain,
    required this.lifetimeActions,
    required this.successCount,
    required this.caughtCount,
    required this.rejectedCount,
    required this.uncertainCount,
    required this.successRate,
    required this.lastActivity,
  });

  factory AgentStatsData.fromJson(Map<String, dynamic> json) {
    final lastActivityRaw = json['last_activity'] as String?;
    return AgentStatsData(
      domain: json['domain'] as String,
      lifetimeActions: json['lifetime_actions'] as int,
      successCount: json['success_count'] as int,
      caughtCount: json['caught_count'] as int,
      rejectedCount: json['rejected_count'] as int,
      uncertainCount: json['uncertain_count'] as int,
      successRate: (json['success_rate'] as num?)?.toDouble(),
      lastActivity: lastActivityRaw == null ? null : DateTime.tryParse(lastActivityRaw),
    );
  }

  bool get isActive => lifetimeActions > 0;
}

/// A real, human-readable relative-activity line -- "Last active 2
/// hours ago" / "Last active 3 days ago" / the honest absence for a
/// real agent that has never acted.
///
/// Deliberately coarse-grained (minutes/hours/days only, never
/// "3847 seconds ago") -- this is a status line for a glance, not a
/// precise timestamp render; `now` is injected so this stays testable
/// without a real clock dependency.
String describeLastActivity(DateTime? lastActivity, {required DateTime now}) {
  if (lastActivity == null) return 'No activity yet';
  final diff = now.difference(lastActivity);
  if (diff.isNegative) return 'Just now';
  if (diff.inMinutes < 1) return 'Just now';
  if (diff.inMinutes < 60) return 'Active ${diff.inMinutes}m ago';
  if (diff.inHours < 24) return 'Active ${diff.inHours}h ago';
  if (diff.inDays < 7) return 'Active ${diff.inDays}d ago';
  final weeks = diff.inDays ~/ 7;
  if (weeks < 5) return 'Active ${weeks}w ago';
  return 'Active over a month ago';
}

/// A real, honest summary line for a success rate -- never a bare
/// percentage with no context about what it's a rate OF.
String describeSuccessRate(AgentStatsData stats) {
  if (!stats.isActive) return 'No real actions yet';
  final rate = stats.successRate;
  if (rate == null) {
    // Genuinely possible: every real resolved action for this agent so
    // far was `outcome_unknown`/`uncertain_no_data` -- an honest "no
    // rate to show," never a fabricated 0%.
    return 'Not enough resolved activity yet';
  }
  final percent = (rate * 100).round();
  return '$percent% approved unchanged';
}
