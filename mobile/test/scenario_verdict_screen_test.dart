// Real widget tests for features/trust/scenario_verdict_screen.dart
// (`DEC-204`, product rebuild) -- the real, full per-scenario verdict
// replay this app has never rendered until now.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/trust/scenario_verdict_screen.dart';
import 'package:quorum_mobile/features/trust/trust_logic.dart';

Widget _harness(ScenarioResultData result) {
  return MaterialApp(home: ScenarioVerdictScreen(result: result));
}

void main() {
  testWidgets('renders a real, passed scenario with its real decision and findings', (tester) async {
    const result = ScenarioResultData(
      scenarioId: 'S0_clean_approval',
      expected: 'approve',
      actual: 'approve',
      passed: true,
      verdict: ScenarioVerdictData(
        decision: 'approve',
        revisionCount: 0,
        findings: [
          FindingSummary(validator: 'ProvenanceCheck', claim: 'A real, distinctive claim', visualState: EvidenceVisualState.positive),
        ],
        objections: [],
        traceId: 'trace-1',
      ),
    );

    await tester.pumpWidget(_harness(result));
    await tester.pumpAndSettle();

    expect(find.text('The Gate caught this real scenario'), findsOneWidget);
    expect(find.text('Real decision: approve'), findsOneWidget);
    expect(find.text('A real, distinctive claim'), findsOneWidget);
    expect(find.text('ProvenanceCheck'), findsOneWidget);
  });

  testWidgets('renders a real, missed scenario honestly, never disguised as a pass', (tester) async {
    const result = ScenarioResultData(
      scenarioId: 'S3_missed',
      expected: 'reject',
      actual: 'approve',
      passed: false,
      verdict: ScenarioVerdictData(decision: 'approve', revisionCount: 0, findings: [], objections: [], traceId: 'trace-2'),
    );

    await tester.pumpWidget(_harness(result));
    await tester.pumpAndSettle();

    expect(find.text('The Gate missed this real scenario'), findsOneWidget);
  });

  testWidgets('a real revision is honestly disclosed, never silently omitted', (tester) async {
    const result = ScenarioResultData(
      scenarioId: 'S2_revised',
      expected: 'revise',
      actual: 'revise',
      passed: true,
      verdict: ScenarioVerdictData(decision: 'revise', revisionCount: 1, findings: [], objections: [], traceId: 'trace-3'),
    );

    await tester.pumpWidget(_harness(result));
    await tester.pumpAndSettle();

    expect(find.text('The Judge revised this proposal before deciding.'), findsOneWidget);
  });

  testWidgets('Stage B is honestly shown as never-run for an S0/S1 scenario, not rendered as a silent pass', (tester) async {
    const result = ScenarioResultData(
      scenarioId: 'S1_no_stage_b',
      expected: 'approve',
      actual: 'approve',
      passed: true,
      verdict: ScenarioVerdictData(decision: 'approve', revisionCount: 0, findings: [], objections: [], traceId: 'trace-4'),
    );

    await tester.pumpWidget(_harness(result));
    await tester.pumpAndSettle();

    expect(find.textContaining('Stage B never ran'), findsOneWidget);
  });

  testWidgets('a real Stage B objection is shown when Stage B genuinely ran', (tester) async {
    const result = ScenarioResultData(
      scenarioId: 'S3_objection',
      expected: 'escalate_to_human',
      actual: 'escalate_to_human',
      passed: true,
      verdict: ScenarioVerdictData(
        decision: 'escalate_to_human',
        revisionCount: 0,
        findings: [],
        objections: [
          ObjectionSummary(category: 'tone', severity: 'high', description: 'A real, distinctive objection', signedOff: false),
        ],
        traceId: 'trace-5',
      ),
    );

    await tester.pumpWidget(_harness(result));
    await tester.pumpAndSettle();

    expect(find.text('A real, distinctive objection'), findsOneWidget);
  });
}
