// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// `DEC-205` (product rebuild) -- the plan's own named "Activity"
// screen: "the full timeline, grouped by day, filterable by agent /
// outcome / stakes." `GET /honesty_log` already carries every real,
// resolved action across three real buckets (successes/failures-and-
// catches/genuinely-uncertain) -- this file merges them back into one
// real, chronological timeline and applies the real, honest filters,
// using nothing but data this backend already computes.

import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

/// Merges the three real buckets `HonestyFeedData` already separates
/// into one real, chronological list, most recent first. Each bucket
/// is already ordered DESC by `fetch_honesty_feed()`'s own real SQL
/// (`ORDER BY ... DESC`), so this is a real three-way merge, not a
/// concatenate-then-sort -- concatenating would put every success
/// before every failure regardless of real timestamp, which would
/// misrepresent the real order these actions actually happened in.
List<LoggedActionData> mergeActivityTimeline(HonestyFeedData feed) {
  final lists = [feed.successes, feed.failuresAndCatches, feed.genuinelyUncertain];
  final indices = List<int>.filled(lists.length, 0);
  final merged = <LoggedActionData>[];
  final totalLength = lists.fold(0, (sum, list) => sum + list.length);

  while (merged.length < totalLength) {
    var bestListIndex = -1;
    for (var i = 0; i < lists.length; i++) {
      if (indices[i] >= lists[i].length) continue;
      if (bestListIndex == -1 || lists[i][indices[i]].timestamp.isAfter(lists[bestListIndex][indices[bestListIndex]].timestamp)) {
        bestListIndex = i;
      }
    }
    merged.add(lists[bestListIndex][indices[bestListIndex]]);
    indices[bestListIndex]++;
  }
  return merged;
}

/// One real calendar day's worth of real activity.
class ActivityDayGroup {
  final DateTime day;
  final List<LoggedActionData> actions;

  const ActivityDayGroup({required this.day, required this.actions});
}

/// Groups an already-chronological (most-recent-first) list by real
/// calendar day, preserving that same order both across and within
/// groups -- never re-sorted, since the caller already did that work.
List<ActivityDayGroup> groupActivityByDay(List<LoggedActionData> actions) {
  final groups = <ActivityDayGroup>[];
  for (final action in actions) {
    final day = DateTime(action.timestamp.year, action.timestamp.month, action.timestamp.day);
    if (groups.isNotEmpty && groups.last.day == day) {
      groups.last.actions.add(action);
    } else {
      groups.add(ActivityDayGroup(day: day, actions: [action]));
    }
  }
  return groups;
}

/// Real, honest filters -- `null` means "no filter on this real
/// dimension," never "show nothing." `domain: null` is a genuinely
/// distinct, selectable filter value from "no domain filter at all"
/// via [matchUnassignedDomain], since a real `CREATE_NOTE` row has no
/// real domain at all and should still be reachable by an explicit
/// choice, not silently excluded forever.
class ActivityFilter {
  final String? domain;
  final String? outcome;
  final String? stakes;
  final bool matchUnassignedDomain;

  const ActivityFilter({this.domain, this.outcome, this.stakes, this.matchUnassignedDomain = false});

  static const ActivityFilter none = ActivityFilter();

  bool get isActive => domain != null || outcome != null || stakes != null || matchUnassignedDomain;
}

List<LoggedActionData> applyActivityFilter(List<LoggedActionData> actions, ActivityFilter filter) {
  return actions.where((action) {
    if (filter.matchUnassignedDomain) {
      if (action.domain != null) return false;
    } else if (filter.domain != null && action.domain != filter.domain) {
      return false;
    }
    if (filter.outcome != null && action.outcome != filter.outcome) return false;
    if (filter.stakes != null && action.stakes != filter.stakes) return false;
    return true;
  }).toList();
}

/// Pure, real, coarse day-header text -- "Today"/"Yesterday" for the
/// two real cases a person actually scans for first, a plain real
/// date otherwise. Both [day] and [now] are expected pre-truncated to
/// a calendar day (callers pass `DateTime(y, m, d)`), so this never
/// does its own truncation and can't silently disagree with
/// [groupActivityByDay]'s own real grouping key.
String formatActivityDayHeader(DateTime day, DateTime today) {
  final difference = today.difference(day).inDays;
  if (difference == 0) return 'Today';
  if (difference == 1) return 'Yesterday';
  return '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';
}
