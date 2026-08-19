/// Real, live backend configuration.
///
/// HONEST NOTE: this is the first time any mobile file in this repository
/// has pointed at a real network address -- every prior session's screens
/// took already-fetched data via a plain constructor parameter, since no
/// live backend existed to call (see `shell/main_shell.dart`'s own
/// disclosed reasoning for why this codebase never built a speculative
/// provider/repository layer). Batch 10 Phases 2-3 changed that: a real
/// Cloud Run service now exists and is genuinely reachable (`DEC-098`,
/// `DEC-102`).
class ApiConfig {
  /// The real, live, deployed backend -- `asia-south1`, matching
  /// Supabase's own region per this project's co-location rule.
  /// `--allow-unauthenticated` as of `DEC-102`: the real application-level
  /// login (`Authorization: Bearer <token>`) is what actually protects
  /// this now, not Cloud Run's network layer.
  static const String baseUrl = 'https://quorum-backend-649581407643.asia-south1.run.app';

  /// The real, live Google OAuth Client ID (`DEC-105`) -- safe to embed
  /// in real app source: OAuth client IDs are not secrets (they appear
  /// in every real authorization request URL already); only the paired
  /// client SECRET is sensitive, and that correctly stays backend-only
  /// (`backend/src/quorum_backend/auth/google_oauth.py`), never sent to
  /// or stored on a real device.
  static const String googleOAuthClientId = '649581407643-6n9j78sares4si1smds7rto7h5lomv8k.apps.googleusercontent.com';
}
