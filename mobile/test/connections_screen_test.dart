// Real widget tests for features/connections/connections_screen.dart
// (`DEC-198`, product rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/connections/connections_logic.dart';
import 'package:quorum_mobile/features/connections/connections_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

Widget _harness({
  required Future<ConnectionHealthData> Function() fetch,
  Future<void> Function()? onReconnect,
}) {
  return MaterialApp(
    theme: buildQuorumDarkTheme(),
    home: ConnectionsScreen(fetch: fetch, onReconnect: onReconnect ?? () async {}),
  );
}

void main() {
  testWidgets('a genuinely absent grant shows the not-connected state and a Connect Google button', (tester) async {
    await tester.pumpWidget(_harness(
      fetch: () async => const ConnectionHealthData(
        connected: false, grantedScopes: [], lastUpdatedAt: null, tokenRefreshable: null,
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Not connected to Google'), findsOneWidget);
    expect(find.text('Connect Google'), findsOneWidget);
    expect(find.text('No Google access granted yet'), findsOneWidget);
  });

  testWidgets('a real, connected and refreshable grant shows its real scopes, humanized, and no reconnect button', (tester) async {
    await tester.pumpWidget(_harness(
      fetch: () async => ConnectionHealthData(
        connected: true,
        grantedScopes: const ['openid', 'https://www.googleapis.com/auth/gmail.send'],
        lastUpdatedAt: DateTime.now().subtract(const Duration(days: 2)),
        tokenRefreshable: true,
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Connected and working'), findsOneWidget);
    expect(find.text('Confirm your identity'), findsOneWidget);
    expect(find.text('Send email on your behalf'), findsOneWidget);
    expect(find.text('Reconnect'), findsNothing);
    expect(find.text('Connect Google'), findsNothing);
  });

  testWidgets('a real, connected but unrefreshable grant honestly shows needs-reconnecting, never silently healthy', (tester) async {
    await tester.pumpWidget(_harness(
      fetch: () async => ConnectionHealthData(
        connected: true,
        grantedScopes: const ['openid'],
        lastUpdatedAt: DateTime.now().subtract(const Duration(days: 10)),
        tokenRefreshable: false,
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Needs reconnecting'), findsOneWidget);
    expect(find.text('Reconnect'), findsOneWidget);
  });

  testWidgets('tapping Reconnect calls the real reconnect callback and refreshes the real status', (tester) async {
    var reconnectCalls = 0;
    var fetchCalls = 0;
    await tester.pumpWidget(_harness(
      fetch: () async {
        fetchCalls++;
        final healthy = fetchCalls > 1;
        return ConnectionHealthData(
          connected: healthy,
          grantedScopes: healthy ? const ['openid'] : const [],
          lastUpdatedAt: healthy ? DateTime.now() : null,
          tokenRefreshable: healthy ? true : null,
        );
      },
      onReconnect: () async {
        reconnectCalls++;
      },
    ));
    await tester.pumpAndSettle();
    expect(find.text('Connect Google'), findsOneWidget);

    await tester.tap(find.text('Connect Google'));
    await tester.pumpAndSettle();

    expect(reconnectCalls, 1);
    expect(fetchCalls, 2);
    expect(find.text('Connected and working'), findsOneWidget);
  });

  testWidgets('a real reconnect failure shows an honest SnackBar, never a crash', (tester) async {
    await tester.pumpWidget(_harness(
      fetch: () async => const ConnectionHealthData(
        connected: false, grantedScopes: [], lastUpdatedAt: null, tokenRefreshable: null,
      ),
      onReconnect: () async => throw Exception('Google rejected this'),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Connect Google'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.textContaining('Google rejected this'), findsOneWidget);
  });

  testWidgets('shows a real, honest error state on a real fetch failure, not a crash', (tester) async {
    await tester.pumpWidget(_harness(fetch: () async => throw Exception('network down')));
    await tester.pumpAndSettle();

    expect(find.textContaining('network down'), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
  });

  testWidgets('tapping Try again genuinely retries without throwing the real setState/Future assertion', (tester) async {
    var attempt = 0;
    await tester.pumpWidget(_harness(
      fetch: () async {
        attempt++;
        if (attempt == 1) throw Exception('network down');
        return const ConnectionHealthData(
          connected: false, grantedScopes: [], lastUpdatedAt: null, tokenRefreshable: null,
        );
      },
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Not connected to Google'), findsOneWidget);
  });
}
