// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Structurally correct against `flutter_test`'s
// documented API; `flutter test` on a real machine is the actual
// verification (MOBILE_01 spec's Step 4).
//
// HONEST DISCREPANCY, disclosed per this project's standing discipline:
// the batch guide's own kickoff prompt for this session said "confirm
// against the 2 real tests in main_shell_test.dart," but MOBILE_01's own
// real spec document (specs/tier4_mobile/MOBILE_01_FLUTTER_SCAFFOLD.md)
// states 3 real tests, named explicitly: all four tabs present, tapping a
// tab genuinely switches content, and the navigation bar has exactly
// four destinations. Built to the spec document's own authoritative
// count, not the kickoff prompt's abbreviated one — see DECISIONS_LOG.md.
//
// A REAL, CASCADING FIX, made in this same session (MOBILE_21), not
// left as a known-broken test: MainShell became a ConsumerStatefulWidget
// when real share-intent wiring was added (reading pendingShareProvider
// via `ref`) -- every pumpWidget call below now wraps MainShell in a
// real ProviderScope, without which a ConsumerStatefulWidget throws
// immediately on build. Confirmed by checking the actual, current
// main_shell.dart rather than assuming the old test still applied.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/shell/main_shell.dart';

void main() {
  testWidgets('all four real tabs are present', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: MainShell())));

    expect(find.text('Today'), findsOneWidget);
    expect(find.text('Log'), findsOneWidget);
    expect(find.text('Trust'), findsOneWidget);
    expect(find.text('You'), findsOneWidget);
  });

  testWidgets('tapping a tab genuinely switches the displayed content',
      (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: MainShell())));

    // Today is the real, default first tab -- its placeholder is shown
    // before any tap happens.
    expect(find.byKey(const Key('placeholder_today')), findsOneWidget);
    expect(find.byKey(const Key('placeholder_log')), findsNothing);

    // A real simulated tap, not a state shortcut.
    await tester.tap(find.text('Log'));
    await tester.pump();

    expect(find.byKey(const Key('placeholder_log')), findsOneWidget);
    expect(find.byKey(const Key('placeholder_today')), findsNothing);
  });

  testWidgets('the navigation bar has exactly four real destinations',
      (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: MainShell())));

    final navigationBar =
        tester.widget<NavigationBar>(find.byType(NavigationBar));

    expect(navigationBar.destinations.length, 4);
  });
}
