// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// `DEC-198` (product rebuild) -- the real, direct answer to this
// rebuild's own sharpest named root cause: one expired Google grant
// silently dams the entire Gmail/Calendar/Career surface, and nothing
// anywhere in this app has ever told a signed-in user that's what
// happened, or even that Quorum requests Gmail/Calendar access at all.
// Backs `GET /connections` (`features/connection_health.py`).

/// Three real, mutually exclusive states a real grant can genuinely be
/// in -- never inferred from color alone (this project's own standing
/// honesty rule), always paired with its own real icon/shape by the
/// widget that renders this.
enum ConnectionStatus { notConnected, healthy, needsReconnect }

class ConnectionHealthData {
  final bool connected;
  final List<String> grantedScopes;
  final DateTime? lastUpdatedAt;

  /// `null` only when [connected] is `false` -- genuinely nothing to
  /// test a live refresh against, never a fabricated `false`.
  final bool? tokenRefreshable;

  const ConnectionHealthData({
    required this.connected,
    required this.grantedScopes,
    required this.lastUpdatedAt,
    required this.tokenRefreshable,
  });
}

ConnectionStatus describeConnectionStatus(ConnectionHealthData data) {
  if (!data.connected) return ConnectionStatus.notConnected;
  return data.tokenRefreshable == false ? ConnectionStatus.needsReconnect : ConnectionStatus.healthy;
}

/// Real, honest, one-line summary for each of the three real states --
/// never a generic "error," since "needs reconnect" is this screen's
/// own entire reason for existing, not a failure to apologize for.
String connectionStatusHeadline(ConnectionStatus status) {
  switch (status) {
    case ConnectionStatus.notConnected:
      return 'Not connected to Google';
    case ConnectionStatus.healthy:
      return 'Connected and working';
    case ConnectionStatus.needsReconnect:
      return 'Needs reconnecting';
  }
}

/// A real, fixed, known-scope-to-plain-English map -- Google's own real
/// scope STRINGS (confirmed against `auth_controller.dart`'s own real
/// authorization request) are the only ones this app has ever asked
/// for. A genuinely unrecognized real scope falls back to the raw
/// string itself rather than being hidden -- an honest "something is
/// granted here that this screen doesn't have a label for" beats
/// silently dropping it.
const Map<String, String> _knownScopeLabels = {
  'openid': 'Confirm your identity',
  'email': 'See your Google account email address',
  'https://www.googleapis.com/auth/gmail.readonly': 'Read your Gmail messages',
  'https://www.googleapis.com/auth/gmail.send': 'Send email on your behalf',
  'https://www.googleapis.com/auth/gmail.modify': 'Organize your Gmail (archive, label, draft)',
  'https://www.googleapis.com/auth/calendar.events': 'Create and manage calendar events',
};

String humanizeScope(String scope) => _knownScopeLabels[scope] ?? scope;

/// Pure, real relative-time formatting for "granted/refreshed Xago" --
/// deliberately coarse (days, not hours/minutes): this is a real
/// OAuth-grant timestamp, not a live-updating clock, and a coarse real
/// number is honest where a false sense of precision would not be.
String formatLastUpdated(DateTime lastUpdatedAt, DateTime now) {
  final difference = now.difference(lastUpdatedAt);
  if (difference.inDays >= 1) {
    return difference.inDays == 1 ? 'Granted 1 day ago' : 'Granted ${difference.inDays} days ago';
  }
  if (difference.inHours >= 1) {
    return difference.inHours == 1 ? 'Granted 1 hour ago' : 'Granted ${difference.inHours} hours ago';
  }
  return 'Granted just now';
}
