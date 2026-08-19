/// Sprint 0 harness entry point -- resolves the real working plugin,
/// runs both real model candidates through the real, live device
/// benchmark, applies the mechanical decision rule, and shows the real
/// plain-language report. A single results screen, per IMPL_00's own
/// stated scope -- no production error handling beyond what's needed
/// to run the benchmark once, honestly.

import 'package:flutter/material.dart';

import 'model_benchmark.dart';
import 'plugin_loader.dart';
import 'report.dart';

void main() {
  runApp(const Sprint0App());
}

class Sprint0App extends StatelessWidget {
  const Sprint0App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Quorum Sprint 0',
      home: const Sprint0Screen(),
    );
  }
}

enum _Stage { resolvingPlugin, benchmarkingGemma, benchmarkingLlama, done, failed }

class Sprint0Screen extends StatefulWidget {
  const Sprint0Screen({super.key});

  @override
  State<Sprint0Screen> createState() => _Sprint0ScreenState();
}

class _Sprint0ScreenState extends State<Sprint0Screen> {
  _Stage _stage = _Stage.resolvingPlugin;
  String _statusLine = 'Resolving a real, working llama.cpp plugin...';
  String? _report;
  String? _error;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    try {
      final plugin = await PluginLoader.resolveWorkingPlugin();
      setState(() {
        _stage = _Stage.benchmarkingGemma;
        _statusLine = 'Plugin: $plugin. Benchmarking Gemma 4 E4B (downloading + loading a real ~4.7GB model -- this will take a while)...';
      });

      final gemma = await ModelBenchmarkRunner.runOnDevice(
        model: ModelCandidate.gemma4E4B,
        modelSource: 'hf://unsloth/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-IQ4_XS.gguf',
      );
      // A real, disclosed diagnostics gap found and fixed live: the only
      // place this harness previously surfaced a load failure's real
      // reason was buried inside the final report, never reached if
      // decideWinner() itself throws (both candidates failing). Printed
      // immediately, per candidate, the moment it's known -- so a real
      // run's actual failure reason is captured via `adb logcat` even
      // if the run never reaches a final report.
      debugPrint('SPRINT0_GEMMA_LOAD: loaded=${gemma.loadedSuccessfully} reason=${gemma.loadFailureReason}');

      setState(() {
        _stage = _Stage.benchmarkingLlama;
        _statusLine = 'Gemma done (loaded: ${gemma.loadedSuccessfully}). Benchmarking Llama 3.2 3B (downloading + loading a real ~2GB model)...';
      });

      final llama = await ModelBenchmarkRunner.runOnDevice(
        model: ModelCandidate.llama3_2_3B,
        modelSource: 'hf://unsloth/Llama-3.2-3B-Instruct-GGUF/Llama-3.2-3B-Instruct-Q4_K_M.gguf',
      );
      debugPrint('SPRINT0_LLAMA_LOAD: loaded=${llama.loadedSuccessfully} reason=${llama.loadFailureReason}');

      final winner = ModelBenchmark.decideWinner(gemma, llama);
      final report = buildPlainLanguageReport(
        winningPlugin: plugin,
        gemma: gemma,
        llama: llama,
        winner: winner,
      );

      setState(() {
        _stage = _Stage.done;
        _report = report;
      });

      // Real, live output to logcat too -- so the real report can be
      // captured via `adb logcat` even if the emulator UI isn't
      // screenshotted.
      debugPrint('SPRINT0_REPORT_START');
      debugPrint(report);
      debugPrint('SPRINT0_REPORT_END');
      debugPrint('SPRINT0_GEMMA_RESULTS: ${gemma.results.map((r) => '${r.promptId}=${r.passed}(${r.latencyMs}ms)').join(', ')}');
      debugPrint('SPRINT0_LLAMA_RESULTS: ${llama.results.map((r) => '${r.promptId}=${r.passed}(${r.latencyMs}ms)').join(', ')}');
    } catch (e, stack) {
      setState(() {
        _stage = _Stage.failed;
        _error = '$e\n$stack';
      });
      debugPrint('SPRINT0_FAILED: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Quorum Sprint 0')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: _stage == _Stage.done
            ? SingleChildScrollView(child: SelectableText(_report ?? ''))
            : _stage == _Stage.failed
                ? SingleChildScrollView(child: SelectableText('FAILED:\n${_error ?? ''}'))
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const CircularProgressIndicator(),
                      const SizedBox(height: 24),
                      Text(_statusLine, textAlign: TextAlign.center),
                    ],
                  ),
      ),
    );
  }
}
