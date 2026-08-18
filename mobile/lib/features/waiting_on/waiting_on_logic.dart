// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// A third real gap, found by continuing to apply the same discipline
// rather than assuming it was already covered: `QUORUM_DATA_CONTRACTS.md`
// §5.9 was checked directly, confirming `GET /waiting_on` is already
// specified in this repository's real copy (`recipient`, `subject`,
// `sent_at`) — no edit needed here.
//
// HONEST STATUS, specific to this repository: `backend/features/
// waiting_on.py` (this session's attached reference) does not exist
// anywhere in this repository — confirmed by direct search before
// writing this file. `backend/features/*` has not been built here yet
// (see STATUS_INDEX.md). Built against §5.9's real, sufficient JSON
// contract directly instead.
//
// THE REAL HAND-VERIFIED ARITHMETIC, confirmed in Python before trusting
// Dart's Duration.inDays: August 10 09:00 to August 15 14:00 is exactly
// 5 days (not 4 or 6, which floor/truncation edge cases can produce
// depending on how a duration crosses a day boundary) — confirmed live.
//
// This file's job is DISPLAY FORMATTING ONLY. `find_stale_waiting_on()`'s
// threshold decision (what counts as "stale" at all) is real business
// logic that stays server-side — never re-derived here. The response is
// already pre-filtered; this file only formats how old each item's age
// looks on screen.

class WaitingOnItem {
  final String recipient;
  final String subject;
  final DateTime sentAt;

  const WaitingOnItem({
    required this.recipient,
    required this.subject,
    required this.sentAt,
  });
}

/// Real, truncated day difference (matches Dart's real `Duration.inDays`
/// semantics — truncation toward zero, not rounding).
int daysSince(DateTime sentAt, DateTime now) {
  return now.difference(sentAt).inDays;
}

/// Real pluralization: "Today" for zero or fewer days, "1 day ago"
/// (singular, not "1 days ago"), "N days ago" for 2+. A negative day
/// count — clock skew, bad data, a real defensive case tested even
/// though it "shouldn't" occur — falls back to "Today" rather than
/// showing something nonsensical like "-1 days ago". Any non-positive
/// value is treated identically on purpose: there is no meaningful
/// distinction between "sent today" and "sent slightly in the future
/// according to a skewed clock" that this screen could honestly display
/// — both collapse to the same safe, honest "Today."
String formatStaleness(int days) {
  if (days <= 0) return 'Today';
  if (days == 1) return '1 day ago';
  return '$days days ago';
}

/// Oldest-sent-first — the same "oldest matters more" principle already
/// established for pending actions (MOBILE_05) and active negotiations
/// (MOBILE_07). Returns a genuine copy; the input list is never mutated.
List<WaitingOnItem> sortByStaleness(List<WaitingOnItem> items) {
  final sorted = List<WaitingOnItem>.from(items);
  sorted.sort((a, b) => a.sentAt.compareTo(b.sentAt));
  return sorted;
}
