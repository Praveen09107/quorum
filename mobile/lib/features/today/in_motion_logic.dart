// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies, same testability tier as the
// other two Today zones — `dart test` is the real verification.
//
// A second real gap, found by applying MOBILE_05's exact discipline
// again, confirmed already fixed in this repository's real copy of
// `QUORUM_DATA_CONTRACTS.md` §5.4 before writing this file, not re-done
// here: the `/today` response's `in_motion` array
// (`negotiation_id`, `conflicted_domains`, `started_at`) is already
// documented, including the F4 source-labeling requirement staying
// intact around it.
//
// The conflict-description logic tested against the exact real domain
// string literals the backend already uses — grepped directly out of
// `backend/tests/test_negotiation_trigger.py` before writing this file's
// tests, confirming this screen's language uses the identical values
// the backend's own two- and three-domain conflict tests exercise:
// "calendar", "finance", "tasks".
//
// Hand-verified in Python before being trusted in Dart:
//   2-domain: 'Calendar vs. Finance'
//   3-domain: 'Calendar vs. Finance vs. Tasks'
//   empty: 'Unknown conflict'
//   single-domain edge case: 'Calendar' (no "vs." separator)

class ActiveNegotiationSummary {
  final String negotiationId;
  final List<String> conflictedDomains;
  final DateTime startedAt;

  const ActiveNegotiationSummary({
    required this.negotiationId,
    required this.conflictedDomains,
    required this.startedAt,
  });
}

String _capitalize(String word) {
  if (word.isEmpty) return word;
  return word[0].toUpperCase() + word.substring(1);
}

/// Real domain-list -> human description. This zone can only ever
/// receive 2- or 3-domain conflicts in practice (the real backend
/// threshold, `backend/src/quorum_backend/negotiation/trigger.py`'s
/// `len(conflicted_list) >= 2`, guarantees negotiation never triggers at
/// 1) — but this function still handles the empty-list and single-domain
/// cases defensively, matching this project's established discipline of
/// degrading gracefully outside a stated contract rather than assuming
/// upstream always behaves.
String describeConflict(List<String> domains) {
  if (domains.isEmpty) return 'Unknown conflict';
  return domains.map(_capitalize).join(' vs. ');
}

/// Ranks OLDEST-started negotiation first — an unresolved conflict
/// that's been sitting longest is the one most worth surfacing, the same
/// "oldest matters more" principle MOBILE_05 established for pending
/// actions. Returns a genuine copy; the input list is never mutated.
List<ActiveNegotiationSummary> sortByStaleness(List<ActiveNegotiationSummary> negotiations) {
  final sorted = List<ActiveNegotiationSummary>.from(negotiations);
  sorted.sort((a, b) => a.startedAt.compareTo(b.startedAt));
  return sorted;
}
