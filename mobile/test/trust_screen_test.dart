// Real widget tests for features/trust/trust_screen.dart's new real
// "Every real scenario" section and tap-through (`DEC-204`, product
// rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/trust/trust_logic.dart';
import 'package:quorum_mobile/features/trust/trust_screen.dart';

const _fakeVerdict = ScenarioVerdictData(decision: 'approve', revisionCount: 0, findings: [], objections: [], traceId: 'trace');

Widget _harness(TrustData trust) {
  return MaterialApp(home: TrustScreen(trust: trust));
}

void main() {
  testWidgets('renders every real scenario from results, not just the missed subset', (tester) async {
    const trust = TrustData(
      total: 2,
      caught: 1,
      missed: [ScenarioResultData(scenarioId: 'S7', expected: 'reject', actual: 'approve', passed: false, verdict: _fakeVerdict)],
      results: [
        ScenarioResultData(scenarioId: 'S1', expected: 'approve', actual: 'approve', passed: true, verdict: _fakeVerdict),
        ScenarioResultData(scenarioId: 'S7', expected: 'reject', actual: 'approve', passed: false, verdict: _fakeVerdict),
      ],
      target: SelfTestTarget.realGate,
    );

    await tester.pumpWidget(_harness(trust));
    await tester.pumpAndSettle();

    expect(find.text('Every real scenario'), findsOneWidget);
    expect(find.text('Scenario S1'), findsWidgets);
    expect(find.text('Scenario S7'), findsWidgets);
  });

  testWidgets('tapping a scenario in "Every real scenario" opens its real Decision replay', (tester) async {
    const trust = TrustData(
      total: 1,
      caught: 1,
      missed: [],
      results: [ScenarioResultData(scenarioId: 'S1_tap_target', expected: 'approve', actual: 'approve', passed: true, verdict: _fakeVerdict)],
      target: SelfTestTarget.realGate,
    );

    await tester.pumpWidget(_harness(trust));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Scenario S1_tap_target'));
    await tester.pumpAndSettle();

    expect(find.text('The Gate caught this real scenario'), findsOneWidget);
  });

  testWidgets('tapping a scenario in "Missed" also opens its real Decision replay', (tester) async {
    const trust = TrustData(
      total: 1,
      caught: 0,
      missed: [ScenarioResultData(scenarioId: 'S9_missed_tap', expected: 'reject', actual: 'approve', passed: false, verdict: _fakeVerdict)],
      results: [ScenarioResultData(scenarioId: 'S9_missed_tap', expected: 'reject', actual: 'approve', passed: false, verdict: _fakeVerdict)],
      target: SelfTestTarget.realGate,
    );

    await tester.pumpWidget(_harness(trust));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Scenario S9_missed_tap').first);
    await tester.pumpAndSettle();

    expect(find.text('The Gate missed this real scenario'), findsOneWidget);
  });

  testWidgets('no "Every real scenario" section appears when results is genuinely empty', (tester) async {
    const trust = TrustData(total: 0, caught: 0, missed: [], results: [], target: SelfTestTarget.realGate);

    await tester.pumpWidget(_harness(trust));
    await tester.pumpAndSettle();

    expect(find.text('Every real scenario'), findsNothing);
  });
}
