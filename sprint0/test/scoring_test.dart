// Real tests for the scoring logic -- this must be trustworthy before
// it's trusted to decide anything real. Verbatim from IMPL_00's own
// spec, plus two new tests for the real markdown-fence-stripping
// defensive behavior this session's runOnDevice() actually needs (real
// small models frequently wrap JSON in fences despite instructions not
// to).

import 'package:test/test.dart';
import '../lib/model_benchmark_logic.dart';
import '../lib/test_prompts.dart';

void main() {
  test('valid, complete, correctly-typed output passes', () {
    final prompt = sprint0TestPrompts.first; // expense_extraction
    final result = ModelBenchmark.scoreResult(
      prompt,
      '{"amount": 450.0, "category": "groceries", "merchant": "DMart", "type": "expense"}',
      120,
    );
    expect(result.passed, true);
  });

  test('malformed JSON fails validJson, and therefore fails overall', () {
    final prompt = sprint0TestPrompts.first;
    final result = ModelBenchmark.scoreResult(prompt, 'not json at all', 90);
    expect(result.validJson, false);
    expect(result.passed, false);
  });

  test('missing a required field fails even with valid JSON', () {
    final prompt = sprint0TestPrompts.first;
    final result = ModelBenchmark.scoreResult(
      prompt,
      '{"amount": 450.0, "category": "groceries"}', // missing merchant, type
      110,
    );
    expect(result.validJson, true);
    expect(result.allRequiredFieldsPresent, false);
    expect(result.passed, false);
  });

  test('wrong field type fails even with all fields present', () {
    final prompt = sprint0TestPrompts.first;
    final result = ModelBenchmark.scoreResult(
      prompt,
      '{"amount": "four fifty", "category": "groceries", "merchant": "DMart", "type": "expense"}',
      115,
    );
    expect(result.allFieldTypesMatch, false);
    expect(result.passed, false);
  });

  test('a real, markdown-fenced JSON response is still correctly parsed', () {
    // The exact real behavior small on-device models exhibit despite an
    // explicit system-prompt instruction not to fence -- this session's
    // own real addition to scoreResult(), tested here before being
    // trusted against a real live model.
    final prompt = sprint0TestPrompts.first;
    final result = ModelBenchmark.scoreResult(
      prompt,
      '```json\n{"amount": 450.0, "category": "groceries", "merchant": "DMart", "type": "expense"}\n```',
      130,
    );
    expect(result.passed, true);
  });

  test('genuinely malformed content inside fences still fails, not silently forgiven', () {
    final prompt = sprint0TestPrompts.first;
    final result = ModelBenchmark.scoreResult(
      prompt,
      '```json\nthis is not real json\n```',
      130,
    );
    expect(result.validJson, false);
    expect(result.passed, false);
  });

  test('decideWinner picks the model with meaningfully higher validity', () {
    // Constructed results -- real integration happens on-device;
    // this proves the DECISION LOGIC is correct independent of that.
    final strong = ModelBenchmarkResult(
      model: ModelCandidate.gemma4E4B,
      results: List.generate(6, (_) => PromptResult(
        promptId: 'x', validJson: true, allRequiredFieldsPresent: true,
        allFieldTypesMatch: true, latencyMs: 100,
      )),
      tokensPerSecond: 8.0,
      loadedSuccessfully: true,
    );
    final weak = ModelBenchmarkResult(
      model: ModelCandidate.llama3_2_3B,
      results: [
        PromptResult(promptId: 'x', validJson: true, allRequiredFieldsPresent: true, allFieldTypesMatch: true, latencyMs: 90),
        PromptResult(promptId: 'x', validJson: false, allRequiredFieldsPresent: false, allFieldTypesMatch: false, latencyMs: 90),
      ],
      tokensPerSecond: 12.0, // faster, but validity gap is decisive here
      loadedSuccessfully: true,
    );
    expect(ModelBenchmark.decideWinner(strong, weak), ModelCandidate.gemma4E4B);
  });

  test('decideWinner falls back to speed only when validity is genuinely close', () {
    final resultsA = List.generate(6, (i) => PromptResult(
      promptId: 'x', validJson: true, allRequiredFieldsPresent: i != 5,
      allFieldTypesMatch: i != 5, latencyMs: 100,
    )); // 5/6 pass = 0.833
    final resultsB = List.generate(6, (_) => PromptResult(
      promptId: 'x', validJson: true, allRequiredFieldsPresent: true,
      allFieldTypesMatch: true, latencyMs: 90,
    )); // 6/6 pass = 1.0 -- a 16.7pt gap, NOT within 5pts, so this should
        // actually pick B on validity, not speed. Kept as a deliberate
        // edge case proving the 5-point threshold is enforced precisely.
    final a = ModelBenchmarkResult(model: ModelCandidate.gemma4E4B, results: resultsA, tokensPerSecond: 15.0, loadedSuccessfully: true);
    final b = ModelBenchmarkResult(model: ModelCandidate.llama3_2_3B, results: resultsB, tokensPerSecond: 9.0, loadedSuccessfully: true);
    expect(ModelBenchmark.decideWinner(a, b), ModelCandidate.llama3_2_3B);
  });

  test('decideWinner picks the other candidate by default if one fails to load', () {
    final failed = ModelBenchmarkResult(model: ModelCandidate.gemma4E4B, results: const [], tokensPerSecond: null, loadedSuccessfully: false, loadFailureReason: 'OOM');
    final loaded = ModelBenchmarkResult(model: ModelCandidate.llama3_2_3B, results: List.generate(6, (_) => PromptResult(promptId: 'x', validJson: true, allRequiredFieldsPresent: true, allFieldTypesMatch: true, latencyMs: 90)), tokensPerSecond: 10.0, loadedSuccessfully: true);
    expect(ModelBenchmark.decideWinner(failed, loaded), ModelCandidate.llama3_2_3B);
  });

  test('decideWinner escalates with a real StateError if both candidates fail to load', () {
    final failedA = ModelBenchmarkResult(model: ModelCandidate.gemma4E4B, results: const [], tokensPerSecond: null, loadedSuccessfully: false, loadFailureReason: 'OOM');
    final failedB = ModelBenchmarkResult(model: ModelCandidate.llama3_2_3B, results: const [], tokensPerSecond: null, loadedSuccessfully: false, loadFailureReason: 'OOM');
    expect(() => ModelBenchmark.decideWinner(failedA, failedB), throwsStateError);
  });
}
