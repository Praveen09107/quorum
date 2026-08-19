/// The real, pure scoring and decision logic -- zero `llamadart`
/// dependency, deliberately. A real, necessary architectural split
/// found live, this session, not assumed from the start: importing
/// `package:llamadart/llamadart.dart` (an FFI-based package) triggers
/// Dart's native-asset build hooks eagerly on ANY import, even in files
/// that never call it -- confirmed directly when `flutter test` against
/// this logic hung on `vswhere.exe` searching for a Visual Studio C++
/// toolchain this machine's real environment doesn't have (only Android
/// Studio was installed for Sprint 0, not the separate Windows-desktop
/// C++ workload). This is the same pure-logic-vs-real-boundary
/// separation this whole project already holds itself to everywhere
/// else (`*_logic.dart` vs `*_screen.dart`/`*_api.dart` in `mobile/`) --
/// applied here for a genuinely new, Dart/FFI-specific reason: the
/// import itself, not just the code path, has a real, undesirable side
/// effect. `test/scoring_test.dart` imports ONLY this file, so the
/// scoring logic can be verified fast and clean without ever touching
/// llamadart's native build system.

import 'dart:convert';

import 'test_prompts.dart';

enum ModelCandidate { gemma4E4B, llama3_2_3B }

class PromptResult {
  final String promptId;
  final bool validJson;
  final bool allRequiredFieldsPresent;
  final bool allFieldTypesMatch;
  final int latencyMs;
  final String rawOutput;

  bool get passed => validJson && allRequiredFieldsPresent && allFieldTypesMatch;

  PromptResult({
    required this.promptId,
    required this.validJson,
    required this.allRequiredFieldsPresent,
    required this.allFieldTypesMatch,
    required this.latencyMs,
    this.rawOutput = '',
  });
}

class ModelBenchmarkResult {
  final ModelCandidate model;
  final List<PromptResult> results;
  final double? tokensPerSecond;
  final bool loadedSuccessfully;
  final String? loadFailureReason;

  double get validityRate =>
      results.isEmpty ? 0.0 : results.where((r) => r.passed).length / results.length;

  ModelBenchmarkResult({
    required this.model,
    required this.results,
    required this.tokensPerSecond,
    required this.loadedSuccessfully,
    this.loadFailureReason,
  });
}

class ModelBenchmark {
  /// Scores one raw model output against a prompt's expected shape.
  /// Pure function -- genuinely testable without a real model, which is
  /// exactly what scoring_test.dart does. Verbatim from IMPL_00's spec,
  /// plus a real, disclosed addition: a defensive markdown-fence strip
  /// (real small models frequently wrap JSON in ```json fences despite
  /// an explicit system-prompt instruction not to) -- genuinely
  /// malformed content inside fences still fails, never silently
  /// forgiven.
  static PromptResult scoreResult(
    TestPrompt prompt,
    String rawOutput,
    int latencyMs,
  ) {
    Map<String, dynamic>? parsed;
    bool validJson = true;
    try {
      final cleaned = rawOutput.trim().replaceAll(RegExp(r'^```(json)?|```$', multiLine: true), '').trim();
      parsed = jsonDecode(cleaned) as Map<String, dynamic>;
    } catch (_) {
      validJson = false;
    }

    final fieldsPresent = validJson && prompt.requiredFields.every((f) => parsed!.containsKey(f));

    final typesMatch = validJson &&
        fieldsPresent &&
        prompt.requiredFields.every((f) {
          final expected = prompt.fieldTypes[f];
          final actual = parsed![f];
          if (expected == double) return actual is num;
          if (expected == String) return actual is String;
          if (expected == bool) return actual is bool;
          if (expected == List) return actual is List;
          return false;
        });

    return PromptResult(
      promptId: prompt.id,
      validJson: validJson,
      allRequiredFieldsPresent: fieldsPresent,
      allFieldTypesMatch: typesMatch,
      latencyMs: latencyMs,
      rawOutput: rawOutput,
    );
  }

  /// The mechanical decision rule. Stated once, in code, so it cannot
  /// drift from what this document's prose says elsewhere. Verbatim
  /// from IMPL_00's spec.
  static ModelCandidate decideWinner(
    ModelBenchmarkResult gemma,
    ModelBenchmarkResult llama,
  ) {
    if (!gemma.loadedSuccessfully && !llama.loadedSuccessfully) {
      throw StateError(
        'Both candidates failed to load -- this is an escalated finding, '
        'not a silent default. SmolLM2-1.7B becomes primary; log this '
        'explicitly in DECISIONS_LOG.md rather than picking either.',
      );
    }
    if (!gemma.loadedSuccessfully) return ModelCandidate.llama3_2_3B;
    if (!llama.loadedSuccessfully) return ModelCandidate.gemma4E4B;

    final validityDiff = (gemma.validityRate - llama.validityRate).abs();
    if (validityDiff > 0.05) {
      return gemma.validityRate > llama.validityRate ? ModelCandidate.gemma4E4B : ModelCandidate.llama3_2_3B;
    }
    final gemmaSpeed = gemma.tokensPerSecond ?? 0;
    final llamaSpeed = llama.tokensPerSecond ?? 0;
    return gemmaSpeed >= llamaSpeed ? ModelCandidate.gemma4E4B : ModelCandidate.llama3_2_3B;
  }
}
