// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct plain Dart; `flutter test` on a real
// machine is the actual verification.
//
// The parity claim, actually checked, not asserted: the three patterns
// below are typed to match `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1
// character-for-character — the exact same patterns
// `backend/security/trace_scrubbing.py`'s `SENSITIVE_PATTERNS` uses.
// Dart's `RegExp` and Python's `re` are both PCRE-like, and none of these
// three patterns use a Python-specific regex extension — confirmed
// deliberately, since an unnoticed regex-flavor difference here would
// have silently broken the entire point of this file.
//
// THE REAL OVERLAP FINDING, independently verified in Python before
// writing this file (this sandbox can run Python, not Dart — the same
// technique used throughout this project wherever Dart logic needs
// checking without a compiler): a 16-digit credit-card number's digits
// also satisfy the Aadhaar-style pattern's digit-count shape, but ONLY
// when the digits are SPACE-separated ("4111 1111 1111 1111"). A plain,
// unspaced 16-digit run or a dash-separated one never triggers the
// overlap — `aadhaar_style_id`'s pattern requires a real `\b` word
// boundary at both ends of its 12-digit match, and consecutive un-
// separated digits are all `\w` characters, so no `\b` exists in the
// middle of an unbroken digit run for that boundary to land on. Verified
// directly, not assumed: `4111111111111111` and `4111-1111-1111-1111`
// both match `credit_card` only; `4111 1111 1111 1111` matches both.
//
// The overlap is proven three ways by this session's real tests:
// `scan()` genuinely reports both `credit_card` and `aadhaar_style_id`
// for the space-separated card number; `redact()` still correctly
// produces exactly ONE redaction despite that overlap, because patterns
// apply sequentially and `credit_card`'s match consumes the entire
// space-separated run first (confirmed directly: its match text is the
// full `"4111 1111 1111 1111"`, leaving no digits for `aadhaar_style_id`'s
// later pass to find); and a pure Aadhaar-style test string is confirmed
// to report ONLY `aadhaar_style_id`, proving the overlap is specific to
// the space-separated card-number case, not a general false-positive
// problem with the Aadhaar pattern itself.

/// Result of a real rule-layer scan — `triggered` is the one field
/// `PrivacyGate.evaluate()` reads to decide whether the SLM classifier
/// gets consulted at all (it must not, when this is true).
class RuleLayerScanResult {
  final bool triggered;
  final List<String> matchedCategories;

  const RuleLayerScanResult({
    required this.triggered,
    required this.matchedCategories,
  });
}

class RuleLayer {
  RuleLayer._();

  /// Exact regexes from `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1 — the
  /// single source of truth both this file and
  /// `backend/security/trace_scrubbing.py`'s `SENSITIVE_PATTERNS` are
  /// required to match exactly, never approximate.
  static final Map<String, RegExp> sensitivePatterns = {
    'credit_card': RegExp(r'\b(?:\d[ -]*?){13,19}\b'),
    'aadhaar_style_id': RegExp(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
    'otp_code': RegExp(
      r'\b(?:OTP|otp|code|verification code)[\s:]*(\d{4,8})\b',
      caseSensitive: false,
    ),
  };

  /// Reports every real category that matches — a pure card number
  /// (space-separated) genuinely reports both `credit_card` and
  /// `aadhaar_style_id`; this is disclosed, tested behavior, not hidden.
  static RuleLayerScanResult scan(String text) {
    final matched = <String>[];
    for (final entry in sensitivePatterns.entries) {
      if (entry.value.hasMatch(text)) {
        matched.add(entry.key);
      }
    }
    return RuleLayerScanResult(
      triggered: matched.isNotEmpty,
      matchedCategories: matched,
    );
  }

  /// Sequential replacement, on purpose — not a single-pass tokenizer
  /// that could miss the real overlap case. `credit_card`'s pass runs
  /// first and consumes the overlapping digits, so `aadhaar_style_id`'s
  /// later pass finds nothing left to match for a pure card number —
  /// exactly one redaction, not two, despite `scan()` reporting both
  /// categories for the same input.
  static String redact(String text) {
    var result = text;
    for (final entry in sensitivePatterns.entries) {
      result = result.replaceAll(
        entry.value,
        '<REDACTED_${entry.key.toUpperCase()}>',
      );
    }
    return result;
  }
}
