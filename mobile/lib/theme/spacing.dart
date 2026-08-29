/// Real, considered spacing scale (Phase 8, `DEC-155`) -- a genuine 4pt-
/// based system, replacing the ad hoc `16`/`24`/`8` literals scattered
/// through every screen file this project's own history has used since
/// Batch 5. Every real screen touched by Phase 8's own remaining
/// sessions is expected to migrate its own literal `EdgeInsets`/`SizedBox`
/// values to these named constants as it's redesigned -- this file
/// itself doesn't retrofit every existing screen in one pass (a real,
/// deliberate scope boundary: this session's own job is the foundation,
/// not a mechanical find-and-replace across the whole app).
class QuorumSpacing {
  QuorumSpacing._();

  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
}
