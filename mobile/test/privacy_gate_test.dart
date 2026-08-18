// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Structurally correct against plain `package:test`'s
// documented API (zero Flutter framework dependency, per this project's
// documented `dart test` vs. `flutter test` distinction). `dart test` on
// a real machine is the actual verification.
//
// HONEST DISCREPANCY, disclosed per this project's standing discipline:
// MOBILE_03's own real spec document
// (specs/tier4_mobile/MOBILE_03_PRIVACY_GATE.md) states 9 real tests
// ("real tests (9/9 — see file)"); the batch guide's pasted checklist
// separately claims 10. This file has 10 -- one more than the spec's
// stated 9, kept and disclosed rather than trimmed, since
// "personal content also proceeds as-is" is a genuinely distinct,
// meaningful case from "public content proceeds as-is" (both are
// no-rule-match outcomes that resolve to the same action via different
// real classifications), not filler. It happens to also match the
// checklist's number, coincidentally, not because the checklist's count
// was treated as authoritative. Every test string below was
// independently checked against the exact same regex patterns in Python
// before being written here (this sandbox can run Python, not Dart) —
// confirming each one exercises exactly the code path it's meant to
// test, not a different one by accident.

import 'package:test/test.dart';

import 'package:quorum_mobile/privacy/privacy_gate.dart';
import 'package:quorum_mobile/privacy/rule_layer.dart';

void main() {
  group('RuleLayer — the real overlap finding, proven three ways', () {
    test('scan() reports BOTH credit_card and aadhaar_style_id for a real space-separated card number', () {
      final result = RuleLayer.scan('4111 1111 1111 1111');
      expect(result.triggered, isTrue);
      expect(result.matchedCategories, containsAll(['credit_card', 'aadhaar_style_id']));
    });

    test('redact() still produces exactly ONE redaction despite that overlap', () {
      final redacted = RuleLayer.redact('4111 1111 1111 1111');
      expect(redacted, '<REDACTED_CREDIT_CARD>');
      expect(redacted.contains('REDACTED'), isTrue);
      // Exactly one placeholder -- credit_card's pass consumes the whole
      // space-separated run first, leaving nothing for aadhaar_style_id's
      // later pass to find.
      expect('REDACTED'.allMatches(redacted).length, 1);
    });

    test('a pure Aadhaar-style string reports ONLY aadhaar_style_id -- the overlap is specific to the card-number case', () {
      final result = RuleLayer.scan('1234 5678 9012');
      expect(result.matchedCategories, ['aadhaar_style_id']);
      expect(result.matchedCategories.contains('credit_card'), isFalse);
    });

    test('a plain, unspaced 16-digit card number does NOT trigger the Aadhaar overlap', () {
      // The real precision finding: the overlap requires a real word
      // boundary landing mid-digit-run, which only a space separator
      // creates. A plain run of digits has no internal \b for
      // aadhaar_style_id's pattern to land on.
      final result = RuleLayer.scan('4111111111111111');
      expect(result.matchedCategories, ['credit_card']);
      expect(result.matchedCategories.contains('aadhaar_style_id'), isFalse);
    });

    test('a dash-separated 16-digit card number does NOT trigger the Aadhaar overlap either', () {
      final result = RuleLayer.scan('4111-1111-1111-1111');
      expect(result.matchedCategories, ['credit_card']);
      expect(result.matchedCategories.contains('aadhaar_style_id'), isFalse);
    });

    test('otp_code redacts the full labeled phrase, not just the bare digits -- parity with the backend', () {
      final redacted = RuleLayer.redact("your code is OTP: 482913, don't share it");
      expect(redacted.contains('482913'), isFalse);
      expect(redacted.contains('OTP: 482913'), isFalse);
      expect(redacted.contains('REDACTED'), isTrue);
    });
  });

  group('PrivacyGate — the real security property', () {
    test('a rule-layer match ALWAYS redacts and NEVER consults the SLM classifier', () async {
      var slmCallCount = 0;
      Future<SensitivityClassification> trackingClassifier(String content) async {
        slmCallCount++;
        return SensitivityClassification.sensitive;
      }

      final gate = PrivacyGate(trackingClassifier);
      final decision = await gate.evaluate('4111 1111 1111 1111');

      expect(decision.action, PrivacyPolicyAction.redactBeforeEscalation);
      expect(decision.slmClassification, isNull);
      expect(decision.ruleMatches, isNotEmpty);
      // Proven by absence of calls, not just correct final state -- the
      // same discipline already established for negotiation's
      // non-conflict short-circuit.
      expect(slmCallCount, 0);
    });

    test('no rule-layer match -- the SLM classifier IS consulted, and public content proceeds as-is', () async {
      var slmCallCount = 0;
      Future<SensitivityClassification> trackingClassifier(String content) async {
        slmCallCount++;
        return SensitivityClassification.public;
      }

      final gate = PrivacyGate(trackingClassifier);
      final decision = await gate.evaluate('the meeting is at 3pm tomorrow');

      expect(decision.action, PrivacyPolicyAction.proceedAsIs);
      expect(decision.slmClassification, SensitivityClassification.public);
      expect(slmCallCount, 1);
    });

    test('personal content (no rule match) also proceeds as-is', () async {
      Future<SensitivityClassification> classifier(String content) async =>
          SensitivityClassification.personal;

      final gate = PrivacyGate(classifier);
      final decision = await gate.evaluate("let's grab dinner Friday");

      expect(decision.action, PrivacyPolicyAction.proceedAsIs);
      expect(decision.slmClassification, SensitivityClassification.personal);
    });

    test('sensitive content (no rule match, SLM-classified) asks the user', () async {
      Future<SensitivityClassification> classifier(String content) async =>
          SensitivityClassification.sensitive;

      final gate = PrivacyGate(classifier);
      final decision = await gate.evaluate('a real but pattern-free sensitive disclosure');

      expect(decision.action, PrivacyPolicyAction.askUser);
      expect(decision.slmClassification, SensitivityClassification.sensitive);
    });
  });
}
