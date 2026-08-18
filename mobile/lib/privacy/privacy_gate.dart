// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct plain Dart; `flutter test` on a real
// machine is the actual verification.
//
// The real policy, and the real proof it's followed correctly: a
// rule-layer match is a FACT, not a judgment call, so it must ALWAYS
// redact and NEVER consult the SLM classifier — this session's test
// proves that by tracking the classifier's actual real invocation count
// and asserting zero, the same "proven by absence of calls, not just
// correct final state" discipline already established for negotiation's
// non-conflict short-circuit (backend IMPL_21, DEC-071).
//
// Out of scope, deliberately: the real on-device SLM call itself.
// MOBILE_02 established that the Full tier's model choice is honestly
// unresolved pending Sprint 0 — SlmClassifier is injected here for the
// same reason every other real/external boundary in this project is
// injected (llm_call, position_call, synthesis_call): this module
// doesn't need to know which model classifies, only that something does.

import 'package:quorum_mobile/privacy/rule_layer.dart';

enum SensitivityClassification { public, personal, sensitive }

enum PrivacyPolicyAction { proceedAsIs, redactBeforeEscalation, askUser }

/// The real, complete outcome of one `PrivacyGate.evaluate()` call.
/// `slmClassification` is explicitly `null` whenever the rule layer
/// already decided — never populated "just in case," since the SLM is
/// never actually consulted in that path.
class PrivacyGateDecision {
  final PrivacyPolicyAction action;
  final String content;
  final List<String> ruleMatches;
  final SensitivityClassification? slmClassification;

  const PrivacyGateDecision({
    required this.action,
    required this.content,
    required this.ruleMatches,
    required this.slmClassification,
  });
}

/// Injected, real/external boundary — genuinely deferred pending
/// MOBILE_02's honestly-unresolved Full-tier model (see model_config.dart).
typedef SlmClassifier = Future<SensitivityClassification> Function(
  String content,
);

class PrivacyGate {
  final SlmClassifier slmClassifier;

  const PrivacyGate(this.slmClassifier);

  Future<PrivacyGateDecision> evaluate(String content) async {
    final ruleResult = RuleLayer.scan(content);

    if (ruleResult.triggered) {
      // THE real security property: a structural pattern match is a fact,
      // not a judgment call. Returns directly here, with
      // slmClassification explicitly null -- BEFORE any call to
      // slmClassifier, not after, not conditionally. Consulting the SLM
      // "just to be safe" here would waste a real cloud/on-device call on
      // an already-decided fact, and worse, would introduce a real path
      // where a probabilistic classifier could override a deterministic,
      // already-correct redaction decision.
      return PrivacyGateDecision(
        action: PrivacyPolicyAction.redactBeforeEscalation,
        content: RuleLayer.redact(content),
        ruleMatches: ruleResult.matchedCategories,
        slmClassification: null,
      );
    }

    final classification = await slmClassifier(content);
    final action = switch (classification) {
      SensitivityClassification.public => PrivacyPolicyAction.proceedAsIs,
      SensitivityClassification.personal => PrivacyPolicyAction.proceedAsIs,
      SensitivityClassification.sensitive => PrivacyPolicyAction.askUser,
    };

    return PrivacyGateDecision(
      action: action,
      content: content,
      ruleMatches: const [],
      slmClassification: classification,
    );
  }
}
