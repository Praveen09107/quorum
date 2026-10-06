// Real tests for features/connections/connections_logic.dart. Zero
// Flutter dependencies, `dart test` is the real verification.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/connections/connections_logic.dart';

ConnectionHealthData _data({
  bool connected = true,
  List<String> grantedScopes = const [],
  DateTime? lastUpdatedAt,
  bool? tokenRefreshable,
}) {
  return ConnectionHealthData(
    connected: connected,
    grantedScopes: grantedScopes,
    lastUpdatedAt: lastUpdatedAt,
    tokenRefreshable: tokenRefreshable,
  );
}

void main() {
  group('describeConnectionStatus', () {
    test('a genuinely absent grant is notConnected', () {
      final status = describeConnectionStatus(_data(connected: false, tokenRefreshable: null));
      expect(status, ConnectionStatus.notConnected);
    });

    test('a connected, refreshable grant is healthy', () {
      final status = describeConnectionStatus(_data(connected: true, tokenRefreshable: true));
      expect(status, ConnectionStatus.healthy);
    });

    test('a connected grant that cannot currently be refreshed needs reconnecting', () {
      final status = describeConnectionStatus(_data(connected: true, tokenRefreshable: false));
      expect(status, ConnectionStatus.needsReconnect);
    });
  });

  group('connectionStatusHeadline', () {
    test('every real status has a real, distinct, non-generic headline', () {
      final headlines = ConnectionStatus.values.map(connectionStatusHeadline).toSet();
      expect(headlines.length, ConnectionStatus.values.length);
      for (final headline in headlines) {
        expect(headline, isNot(contains('error')));
      }
    });
  });

  group('humanizeScope', () {
    test('a real, known Google scope is translated to plain English', () {
      expect(humanizeScope('https://www.googleapis.com/auth/gmail.send'), 'Send email on your behalf');
      expect(humanizeScope('openid'), 'Confirm your identity');
    });

    test('a genuinely unrecognized real scope falls back to the raw string, never hidden', () {
      expect(humanizeScope('https://www.googleapis.com/auth/some.new.scope'), 'https://www.googleapis.com/auth/some.new.scope');
    });
  });

  group('formatLastUpdated', () {
    final now = DateTime.utc(2026, 10, 6, 12, 0, 0);

    test('under an hour ago reads as just now', () {
      expect(formatLastUpdated(now.subtract(const Duration(minutes: 10)), now), 'Granted just now');
    });

    test('hours ago are pluralized correctly', () {
      expect(formatLastUpdated(now.subtract(const Duration(hours: 1)), now), 'Granted 1 hour ago');
      expect(formatLastUpdated(now.subtract(const Duration(hours: 5)), now), 'Granted 5 hours ago');
    });

    test('days ago are pluralized correctly', () {
      expect(formatLastUpdated(now.subtract(const Duration(days: 1)), now), 'Granted 1 day ago');
      expect(formatLastUpdated(now.subtract(const Duration(days: 3)), now), 'Granted 3 days ago');
    });
  });
}
