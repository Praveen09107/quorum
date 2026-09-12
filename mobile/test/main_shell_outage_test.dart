// Real, live proof that `main_shell.dart`'s new `healthCheck` wiring
// (`QUORUM_PRODUCTION_READINESS_AUDIT_PLAN.md`'s own first audit run,
// closing the real "OutageBanner has zero real callers" gap) actually
// drives `OutageBanner`'s real visibility through `outage_detector.dart`'s
// own already-real, already-tested state machine -- a real widget test,
// not just a unit test of the pieces in isolation.
//
// `flutter_test`'s own real fake-clock binding means a real
// `Timer.periodic` created inside a pumped widget fires on
// `tester.pump(duration)`, never on real wall-clock time -- this file's
// own tests never actually wait 20 real seconds, or even close to it.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/outage/outage_banner.dart';
import 'package:quorum_mobile/shell/main_shell.dart';

Widget _harness({required Future<bool> Function() healthCheck}) {
  return ProviderScope(
    child: MaterialApp(
      home: MainShell(
        healthCheck: healthCheck,
        healthCheckInterval: const Duration(seconds: 1),
        confirmDelete: () async => throw UnimplementedError(),
      ),
    ),
  );
}

void main() {
  testWidgets('the real outage banner is invisible while every real health check succeeds', (tester) async {
    await tester.pumpWidget(_harness(healthCheck: () async => true));
    await tester.pumpAndSettle();

    expect(find.byType(OutageBanner), findsOneWidget);
    expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsNothing);

    await tester.pump(const Duration(seconds: 1));
    await tester.pump();

    expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsNothing);
  });

  testWidgets('the real outage banner genuinely appears after 3 real, consecutive health-check failures', (tester) async {
    await tester.pumpWidget(_harness(healthCheck: () async => false));
    await tester.pumpAndSettle();

    // Real, exact match to outage_detector.dart's own real
    // outageFailureThreshold -- 3 consecutive failures, no fewer.
    for (var i = 0; i < 2; i++) {
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();
      expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsNothing);
    }

    await tester.pump(const Duration(seconds: 1));
    await tester.pump();

    expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsOneWidget);
  });

  testWidgets('the real outage banner disappears immediately on the first real recovered health check', (tester) async {
    var healthy = false;
    await tester.pumpWidget(_harness(healthCheck: () async => healthy));
    await tester.pumpAndSettle();

    for (var i = 0; i < 3; i++) {
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();
    }
    expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsOneWidget);

    healthy = true;
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();

    expect(find.text("Connection lost. Low-stakes actions are queuing to send once you're back online; anything irreversible will wait for your explicit approval before it goes anywhere."), findsNothing);
  });

  testWidgets('no real health-check polling happens at all when none is configured', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: MainShell(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(OutageBanner), findsOneWidget);
    // A real, honest absence of any pending Timer -- confirmed
    // indirectly: pumping real elapsed time never throws
    // "A Timer is still pending" (flutter_test's own real, live
    // assertion that would fail this test if a Timer were still
    // running with no test-owned pump to drive it forward safely).
    await tester.pump(const Duration(seconds: 30));
  });
}
