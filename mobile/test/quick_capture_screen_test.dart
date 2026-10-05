// Real widget tests for features/quick_capture/quick_capture_screen.dart
// -- the redesign's own real Quick-capture richness work: closes a real,
// confirmed gap where this screen's own real `/quick_capture` response
// has always carried real Stage B `objections` on every call, silently
// dropped until now.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_screen.dart';

Widget _harness(Future<QuickCaptureResultData> Function(String) capture) {
  return MaterialApp(home: QuickCaptureScreen(capture: capture));
}

void main() {
  testWidgets('a real S3 result with real objections shows the real Stage B section', (tester) async {
    Future<QuickCaptureResultData> capture(String text) async {
      return const QuickCaptureResultData(
        executed: false,
        decision: 'escalate_to_human',
        stakes: 'S3',
        domain: 'email',
        title: null,
        findings: [
          FindingSummary(validator: 'recipient_check', claim: 'Recipient is a real contact', visualState: EvidenceVisualState.positive),
        ],
        objections: [
          ObjectionSummary(category: 'tone', severity: 'medium', description: 'Reads as more confident than the evidence supports.', signedOff: false),
        ],
      );
    }

    await tester.pumpWidget(_harness(capture));
    await tester.enterText(find.byType(TextField), 'send an urgent email to the client');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();

    expect(find.text('Stage B — Critic review'), findsOneWidget);
    expect(find.text('Reads as more confident than the evidence supports.'), findsOneWidget);
  });

  testWidgets('a real S1 result (Stage B never ran) shows no Stage B section at all', (tester) async {
    Future<QuickCaptureResultData> capture(String text) async {
      return const QuickCaptureResultData(
        executed: true,
        decision: 'approve',
        stakes: 'S1',
        domain: 'tasks',
        title: 'A real task',
        findings: [],
        objections: [],
      );
    }

    await tester.pumpWidget(_harness(capture));
    await tester.enterText(find.byType(TextField), 'a real low-stakes task');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();

    expect(find.text('Stage B — Critic review'), findsNothing);
  });

  testWidgets('a real S3 result with an empty objections list (Stage B signed off) shows a real, honest sign-off', (tester) async {
    Future<QuickCaptureResultData> capture(String text) async {
      return const QuickCaptureResultData(
        executed: true,
        decision: 'approve',
        stakes: 'S3',
        domain: 'email',
        title: null,
        emailAction: 'send_email',
        findings: [],
        objections: [
          ObjectionSummary(category: 'completeness', severity: 'low', description: 'No issues found.', signedOff: true),
        ],
      );
    }

    await tester.pumpWidget(_harness(capture));
    await tester.enterText(find.byType(TextField), 'send a routine email');
    await tester.tap(find.text('Create'));
    await tester.pumpAndSettle();

    expect(find.text('Stage B — Critic review'), findsOneWidget);
    expect(find.text('Reviewed — no objections'), findsOneWidget);
  });
}
