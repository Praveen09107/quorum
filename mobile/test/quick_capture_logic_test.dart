// Real tests for features/quick_capture/quick_capture_logic.dart
// (`DEC-153`). Zero Flutter dependencies -- `dart test` is the real
// command.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';

void main() {
  group('describeQuickCaptureOutcome', () {
    test('a genuine approve names the real, created task title', () {
      const result = QuickCaptureResultData(
        executed: true, decision: 'approve', stakes: 'S1', title: 'Finish the Q3 budget review', findings: [],
      );
      expect(describeQuickCaptureOutcome(result), 'Created: Finish the Q3 budget review');
    });

    test('a real Stage A revise gives an honest, distinct message, never a fabricated title', () {
      const result = QuickCaptureResultData(executed: false, decision: 'revise', stakes: 'S1', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains("couldn't create"));
    });

    test('a real escalate_to_human gives an honest, distinct message', () {
      const result = QuickCaptureResultData(executed: false, decision: 'escalate_to_human', stakes: 'S3', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains('your direct approval'));
    });

    test('a real reject gives an honest, distinct message', () {
      const result = QuickCaptureResultData(executed: false, decision: 'reject', stakes: 'S1', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains('declined'));
    });

    test('an unrecognized real decision falls back to a real, generic honest message, never a crash', () {
      const result = QuickCaptureResultData(executed: false, decision: 'something_new', stakes: 'S1', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), 'That task was not created.');
    });
  });

  test('FindingSummary/EvidenceVisualState are genuinely reused, not redefined', () {
    // A real, direct proof this file imports the real gate_reveal_logic.dart
    // types rather than shadowing them with a second, parallel definition.
    const summary = FindingSummary(validator: 'provenance_check', claim: 'A real claim', visualState: EvidenceVisualState.positive);
    const result = QuickCaptureResultData(executed: true, decision: 'approve', stakes: 'S1', title: 'A real task', findings: [summary]);
    expect(result.findings.single.visualState, EvidenceVisualState.positive);
  });
}
