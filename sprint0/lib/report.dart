/// Produces the plain-language report -- this is what the developer
/// actually reads. No code, no jargon beyond what's necessary, a direct
/// approve/proceed signal, per this project's own stated requirement
/// that verification results reach a non-code-reading developer as
/// prose, not diffs. Verbatim from IMPL_00's own spec.

import 'model_benchmark.dart';
import 'plugin_loader.dart';

String buildPlainLanguageReport({
  required PluginCandidate winningPlugin,
  required ModelBenchmarkResult gemma,
  required ModelBenchmarkResult llama,
  required ModelCandidate winner,
}) {
  final winnerName = winner == ModelCandidate.gemma4E4B ? 'Gemma 4 E4B' : 'Llama 3.2 3B';
  final gemmaRate = (gemma.validityRate * 100).toStringAsFixed(0);
  final llamaRate = (llama.validityRate * 100).toStringAsFixed(0);

  final gemmaLoadNote = gemma.loadedSuccessfully ? '' : ' (FAILED TO LOAD: ${gemma.loadFailureReason})';
  final llamaLoadNote = llama.loadedSuccessfully ? '' : ' (FAILED TO LOAD: ${llama.loadFailureReason})';

  return '''
SPRINT 0 -- RESULTS

Plugin: $winningPlugin loaded successfully and is now the runtime for
all future on-device work.

Gemma 4 E4B: $gemmaRate% of test prompts produced correct, usable output
(${gemma.tokensPerSecond?.toStringAsFixed(1) ?? "n/a"} tokens/second)$gemmaLoadNote.

Llama 3.2 3B: $llamaRate% of test prompts produced correct, usable output
(${llama.tokensPerSecond?.toStringAsFixed(1) ?? "n/a"} tokens/second)$llamaLoadNote.

WINNER: $winnerName. This is now the permanent on-device primary model,
written into QUORUM_CONFIGURATION_CONSTANTS.md. No further sessions will
ask this question again.

Next: MOBILE_01, the Flutter app scaffold.
''';
}
