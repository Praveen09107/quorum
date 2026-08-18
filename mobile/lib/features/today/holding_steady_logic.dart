// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies, same testability tier as
// MOBILE_05 — `dart test` is the real verification.
//
// The two-touchpoint framing from the retention rethink, made real
// (ADD §12.2): two natural daily touchpoints bookend the day -- a
// morning "what does today look like" and an evening "how did today
// go" -- deliberately NOT gamification: no streak, no score, no count,
// no social/comparative mechanic. Confirmed by direct inspection: this
// file contains no such logic anywhere.
//
// THE REAL BOUNDARY LOGIC, hand-verified in Python across every real
// edge hour before being trusted in Dart:
//   11:00 -> morning, 12:00 -> midday, 17:00 -> midday, 18:00 -> evening,
//   0:00 -> morning, 23:00 -> evening   -- ALL PASS

enum DayTouchpoint { morning, midday, evening }

/// Real, exact hour boundaries -- hour < 12 is morning, hour >= 18 is
/// evening, everything between is a genuinely neutral midday.
DayTouchpoint classifyTouchpoint(int hour) {
  if (hour < 12) return DayTouchpoint.morning;
  if (hour >= 18) return DayTouchpoint.evening;
  return DayTouchpoint.midday;
}

/// Real, honest headlines -- no streaks, no scores, no "X days in a row."
/// Midday deliberately gets a genuinely neutral label, distinct from
/// both bookends: it's neither "what does today look like" (that
/// question was already answered this morning) nor "how did today go"
/// (that question isn't answerable yet) -- a real third state, not a
/// forced fit into either framing.
String touchpointHeadline(DayTouchpoint touchpoint) {
  switch (touchpoint) {
    case DayTouchpoint.morning:
      return 'What does today look like';
    case DayTouchpoint.midday:
      return 'Holding steady';
    case DayTouchpoint.evening:
      return 'How did today go';
  }
}
