// Real tests for features/quick_capture/quick_capture_logic.dart
// (`DEC-153`). Zero Flutter dependencies -- `dart test` is the real
// command.
//
// REAL, DISCLOSED SESSION-4 EXTENSION: `domain` is now a real, required
// field on `QuickCaptureResultData` -- every existing construction below
// gained a real `domain: 'tasks'`, matching the real backend's own
// `QuickCaptureResult.domain` contract, which is likewise always
// present. A new `group('finance domain')` below covers the genuinely
// new Finance-domain branch.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';

void main() {
  group('describeQuickCaptureOutcome', () {
    test('a genuine approve names the real, created task title', () {
      const result = QuickCaptureResultData(
        executed: true, decision: 'approve', stakes: 'S1', domain: 'tasks', title: 'Finish the Q3 budget review', findings: [],
      );
      expect(describeQuickCaptureOutcome(result), 'Created: Finish the Q3 budget review');
    });

    test('a real Stage A revise gives an honest, distinct message, never a fabricated title', () {
      const result = QuickCaptureResultData(executed: false, decision: 'revise', stakes: 'S1', domain: 'tasks', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains("couldn't create"));
    });

    test('a real escalate_to_human gives an honest, distinct message', () {
      const result = QuickCaptureResultData(executed: false, decision: 'escalate_to_human', stakes: 'S3', domain: 'tasks', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains('your direct approval'));
    });

    test('a real reject gives an honest, distinct message', () {
      const result = QuickCaptureResultData(executed: false, decision: 'reject', stakes: 'S1', domain: 'tasks', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains('declined'));
    });

    test('an unrecognized real decision falls back to a real, generic honest message, never a crash', () {
      const result = QuickCaptureResultData(executed: false, decision: 'something_new', stakes: 'S1', domain: 'tasks', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), 'That was not created.');
    });
  });

  group('describeQuickCaptureOutcome -- finance domain (Session 4)', () {
    test('a genuine log_expense approve shows a real, formatted amount and category', () {
      const result = QuickCaptureResultData(
        executed: true, decision: 'approve', stakes: 'S1', domain: 'finance',
        title: null, amount: 800.0, category: 'groceries', financeAction: 'log_expense', findings: [],
      );
      expect(describeQuickCaptureOutcome(result), 'Logged: ₹800 -- groceries');
    });

    test('a genuine update_budget approve shows a real, formatted new ceiling, never a task title', () {
      const result = QuickCaptureResultData(
        executed: true, decision: 'approve', stakes: 'S2', domain: 'finance',
        title: null, amount: 60000.0, category: 'monthly budget', financeAction: 'update_budget', findings: [],
      );
      expect(describeQuickCaptureOutcome(result), 'Budget updated to ₹60000');
    });

    test('a real finance revise gives the same honest, distinct message as tasks', () {
      const result = QuickCaptureResultData(executed: false, decision: 'revise', stakes: 'S2', domain: 'finance', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains("couldn't create"));
    });

    test('a real finance escalate_to_human (genuinely reachable -- UPDATE_BUDGET is real Stakes.S2) gives an honest message', () {
      const result = QuickCaptureResultData(executed: false, decision: 'escalate_to_human', stakes: 'S2', domain: 'finance', title: null, findings: []);
      expect(describeQuickCaptureOutcome(result), contains('your direct approval'));
    });
  });

  test('FindingSummary/EvidenceVisualState are genuinely reused, not redefined', () {
    // A real, direct proof this file imports the real gate_reveal_logic.dart
    // types rather than shadowing them with a second, parallel definition.
    const summary = FindingSummary(validator: 'provenance_check', claim: 'A real claim', visualState: EvidenceVisualState.positive);
    const result = QuickCaptureResultData(executed: true, decision: 'approve', stakes: 'S1', domain: 'tasks', title: 'A real task', findings: [summary]);
    expect(result.findings.single.visualState, EvidenceVisualState.positive);
  });
}
