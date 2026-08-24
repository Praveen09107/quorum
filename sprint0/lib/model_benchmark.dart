/// The real, live device-calling layer -- imports `llamadart` (an FFI
/// package whose mere import triggers native build hooks, see
/// `model_benchmark_logic.dart`'s own header for why that logic lives
/// in a separate, llamadart-free file). This file is only ever imported
/// by real, on-device-running code (`main.dart`), never by
/// `test/scoring_test.dart`.

import 'package:llamadart/llamadart.dart';

import 'model_benchmark_logic.dart';
import 'plugin_loader.dart';
import 'test_prompts.dart';

export 'model_benchmark_logic.dart';

class ModelBenchmarkRunner {
  /// Runs one real candidate through the real, live llamadart engine
  /// against every real test prompt. `modelSource` is a real `hf://`
  /// reference -- letting llamadart's own real, already-tested
  /// download+cache logic handle on-device storage placement, rather
  /// than this session inventing its own adb-push/storage-permission
  /// handling for a one-off benchmark harness.
  static Future<ModelBenchmarkResult> runOnDevice({
    required ModelCandidate model,
    required String modelSource,
  }) async {
    final engine = LlamaEngine(LlamaBackend());
    try {
      // Real retry against a real, diagnosed-live intermittent DNS flake
      // on this session's test device -- see PluginLoader.loadModelWithDnsRetry's
      // own header for the full, real root-cause explanation.
      await PluginLoader.loadModelWithDnsRetry(engine, modelSource);
    } catch (e) {
      return ModelBenchmarkResult(
        model: model,
        results: const [],
        tokensPerSecond: null,
        loadedSuccessfully: false,
        loadFailureReason: e.toString(),
      );
    }

    final results = <PromptResult>[];
    var totalTokens = 0;
    var totalElapsedMs = 0;

    for (final prompt in sprint0TestPrompts) {
      final stopwatch = Stopwatch()..start();
      final buffer = StringBuffer();
      var generatedTokens = 0;
      try {
        final stream = engine.create(
          [
            LlamaChatMessage.fromText(role: LlamaChatRole.system, text: systemPromptFor(prompt)),
            LlamaChatMessage.fromText(role: LlamaChatRole.user, text: prompt.input),
          ],
          params: const GenerationParams(maxTokens: 128, temp: 0.1),
        );
        await for (final chunk in stream) {
          final content = chunk.choices.first.delta.content;
          if (content != null && content.isNotEmpty) {
            buffer.write(content);
            generatedTokens++;
          }
        }
      } catch (e) {
        // A real, live generation failure for this one prompt -- scored
        // as a real fail (invalid output), not silently skipped or
        // allowed to crash the whole benchmark run.
        results.add(PromptResult(
          promptId: prompt.id,
          validJson: false,
          allRequiredFieldsPresent: false,
          allFieldTypesMatch: false,
          latencyMs: stopwatch.elapsedMilliseconds,
          rawOutput: 'GENERATION_ERROR: $e',
        ));
        continue;
      }
      stopwatch.stop();

      results.add(ModelBenchmark.scoreResult(prompt, buffer.toString(), stopwatch.elapsedMilliseconds));
      totalTokens += generatedTokens;
      totalElapsedMs += stopwatch.elapsedMilliseconds;
    }

    await engine.dispose();

    final tokensPerSecond = totalElapsedMs > 0 ? totalTokens / (totalElapsedMs / 1000) : null;

    return ModelBenchmarkResult(
      model: model,
      results: results,
      tokensPerSecond: tokensPerSecond,
      loadedSuccessfully: true,
    );
  }
}
