// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// THE REAL, LOAD-BEARING PROPERTY these tests exist to prove: an empty
// objections list means Stage B never ran; a list containing ONLY a
// sign-off entry means Stage B ran and found nothing to object to. These
// are genuinely different real states this file must never conflate.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

ObjectionSummary _signOffEntry() => const ObjectionSummary(
      category: 'completeness',
      severity: 'low',
      description: 'Reviewed the full proposal against the real evidence -- no issues found.',
      signedOff: true,
    );

ObjectionSummary _realObjection() => const ObjectionSummary(
      category: 'tone',
      severity: 'medium',
      description: 'The draft reads as more confident than the underlying evidence supports.',
      signedOff: false,
    );

void main() {
  group('visualStateForEvidence -- the real three-valued mapping, never collapsed', () {
    test('verified_true maps to positive', () {
      expect(visualStateForEvidence('verified_true'), EvidenceVisualState.positive);
    });

    test('verified_false maps to negative', () {
      expect(visualStateForEvidence('verified_false'), EvidenceVisualState.negative);
    });

    test('no_data_found maps to a genuinely distinct uncertain state -- never a pass, never a fail', () {
      final state = visualStateForEvidence('no_data_found');
      expect(state, EvidenceVisualState.uncertain);
      expect(state, isNot(EvidenceVisualState.positive));
      expect(state, isNot(EvidenceVisualState.negative));
    });

    test('an unrecognized evidence_state value defensively maps to uncertain, never a silent pass', () {
      expect(visualStateForEvidence('something_new_the_backend_might_add'), EvidenceVisualState.uncertain);
    });
  });

  group('stageBRan -- THE real, load-bearing check', () {
    test('an empty objections list means Stage B genuinely never ran', () {
      expect(stageBRan(const []), isFalse);
    });

    test('a sign-off-ONLY list means Stage B ran and found nothing to object to -- NOT "never ran"', () {
      expect(stageBRan([_signOffEntry()]), isTrue);
    });

    test('a list with a real objection also means Stage B ran', () {
      expect(stageBRan([_realObjection()]), isTrue);
    });
  });

  group('stageBRanForStakes -- the real check GateRevealScreen actually uses (DEC-146)', () {
    test('S0 never reaches Stage B', () {
      expect(stageBRanForStakes('S0'), isFalse);
    });

    test('S1 never reaches Stage B', () {
      expect(stageBRanForStakes('S1'), isFalse);
    });

    test('S2 reaches Stage B (the Judge only) -- even though the Critic never ran and objections may be empty', () {
      expect(stageBRanForStakes('S2'), isTrue);
    });

    test('S3 reaches Stage B (Critic then Judge)', () {
      expect(stageBRanForStakes('S3'), isTrue);
    });
  });

  group('summarizeStageB', () {
    test('a sign-off-only list produces zero real objections and signedOff=true', () {
      final summary = summarizeStageB([_signOffEntry()]);
      expect(summary.realObjections, isEmpty);
      expect(summary.signedOff, isTrue);
    });

    test('a real-objections-only list produces those objections and signedOff=false', () {
      final summary = summarizeStageB([_realObjection()]);
      expect(summary.realObjections.length, 1);
      expect(summary.signedOff, isFalse);
    });

    test('the defensive mixed case -- a real objection alongside a sign-off entry -- is still handled sensibly', () {
      // The real schema says this shouldn't occur, but real code should
      // degrade gracefully even outside its stated contract.
      final summary = summarizeStageB([_realObjection(), _signOffEntry()]);
      expect(summary.realObjections.length, 1);
      expect(summary.realObjections.first.signedOff, isFalse);
      expect(summary.signedOff, isTrue);
    });
  });
}
