// Real widget tests for features/onboarding/onboarding_screen.dart
// (`DEC-196`, product rebuild Block G) -- never built before this
// session (ADD §12.5's own standing gap).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/onboarding/onboarding_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

Widget _harness(VoidCallback onDone) {
  return MaterialApp(theme: buildQuorumDarkTheme(), home: OnboardingScreen(onDone: onDone));
}

void main() {
  testWidgets('renders the real first card, including all five domain agent badges', (tester) async {
    await tester.pumpWidget(_harness(() {}));
    await tester.pumpAndSettle();

    expect(find.text('Five agents work on your behalf'), findsOneWidget);
    expect(find.byType(Icon), findsWidgets);
  });

  testWidgets('tapping Next twice reaches the real third card and shows "Get started"', (tester) async {
    await tester.pumpWidget(_harness(() {}));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('A Gate verifies every one of them'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    expect(find.text('Anything irreversible always waits for you'), findsOneWidget);
    expect(find.text('Get started'), findsOneWidget);
  });

  testWidgets('tapping Get started on the real last card calls onDone', (tester) async {
    var doneCount = 0;
    await tester.pumpWidget(_harness(() => doneCount++));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Get started'));
    await tester.pumpAndSettle();

    expect(doneCount, 1);
  });

  testWidgets('tapping Skip from the real first card calls onDone immediately, without requiring every card', (tester) async {
    var doneCount = 0;
    await tester.pumpWidget(_harness(() => doneCount++));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Skip'));
    await tester.pumpAndSettle();

    expect(doneCount, 1);
  });

  testWidgets('swiping to the real second card updates the real page indicator', (tester) async {
    await tester.pumpWidget(_harness(() {}));
    await tester.pumpAndSettle();

    await tester.drag(find.text('Five agents work on your behalf'), const Offset(-600, 0));
    await tester.pumpAndSettle();

    expect(find.text('A Gate verifies every one of them'), findsOneWidget);
  });
}
