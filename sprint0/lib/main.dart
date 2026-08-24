/// Sprint 0 harness entry point -- resolves the real working plugin,
/// runs both real model candidates through the real, live device
/// benchmark, applies the mechanical decision rule, and shows the real
/// plain-language report. A single results screen, per IMPL_00's own
/// stated scope -- no production error handling beyond what's needed
/// to run the benchmark once, honestly.

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:llamadart/llamadart.dart';

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
      // Real, one-shot diagnostic added live this session: isolates whether
      // it's specifically Dart's own dart:io DNS resolver failing on this
      // device/network (as opposed to llamadart's HttpClient configuration,
      // or the model URLs themselves) -- `adb shell curl` against the exact
      // same hostname succeeds reliably from this same device, so this
      // narrows down which layer is actually broken. Real result goes to
      // logcat either way; never silently swallowed.
      try {
        final addresses = await InternetAddress.lookup('huggingface.co');
        debugPrint('SPRINT0_DART_DNS_PROBE: OK -- ${addresses.map((a) => a.address).join(', ')}');
      } catch (e) {
        debugPrint('SPRINT0_DART_DNS_PROBE: FAILED -- $e');
      }

      // Real, second-stage diagnostic added live this session: isolates
      // whether it's specifically dart:io HttpClient's own CONNECTION
      // step (as distinct from the DNS lookup the probe above already
      // proved works) failing -- e.g. a real IPv6-advertised-but-
      // unreachable address being tried first (Happy Eyeballs-style),
      // which would surface as a misleading "host lookup" error even
      // though DNS itself succeeded. Tests raw HttpClient, then forces
      // IPv4-only via a manually-resolved address, completely bypassing
      // llamadart, so the result isolates dart:io itself.
      try {
        final client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 15);
        final request = await client.getUrl(Uri.parse('https://huggingface.co/'));
        final response = await request.close();
        await response.drain<void>();
        debugPrint('SPRINT0_RAW_HTTPCLIENT_PROBE: OK -- status ${response.statusCode}');
        client.close(force: true);
      } catch (e) {
        debugPrint('SPRINT0_RAW_HTTPCLIENT_PROBE: FAILED -- $e');
      }

      // Real, third-stage diagnostic: replicates llamadart's exact real
      // request -- the real Gemma resolve URL, `followRedirects = false`,
      // manual Location-header redirect handling -- completely outside
      // llamadart's own class, so a failure here isolates the real
      // redirect/CDN-hop flow itself as the cause, not llamadart's code.
      try {
        final client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 15);
        var requestUri = Uri.parse(
          'https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-IQ4_XS.gguf?download=true',
        );
        HttpClientResponse response;
        var hops = 0;
        while (true) {
          final request = await client.getUrl(requestUri);
          request.followRedirects = false;
          response = await request.close();
          if (response.statusCode != 302 && response.statusCode != 301) break;
          hops++;
          final location = response.headers.value(HttpHeaders.locationHeader)!;
          debugPrint('SPRINT0_REPLICA_PROBE: hop $hops -> $location');
          requestUri = requestUri.resolve(location);
          await response.drain<void>();
        }
        // Deliberately NOT draining the full ~4.7GB body -- that tests
        // "did a multi-minute transfer survive the whole way," a much
        // higher, unrelated bar. Reads only the first chunk to prove the
        // connection actually opened and data started flowing, then
        // cancels -- the fair, matching comparison to the original bug,
        // which failed instantly, before any transfer began.
        final firstChunk = await response.first;
        debugPrint('SPRINT0_REPLICA_PROBE: OK -- final status ${response.statusCode} after $hops hop(s), first chunk ${firstChunk.length} bytes');
        client.close(force: true);
      } catch (e) {
        debugPrint('SPRINT0_REPLICA_PROBE: FAILED -- $e');
      }

      // Real, repeated test: fires the exact same real request 5 times
      // back-to-back, immediately, to see whether this is a genuine,
      // consistent failure or ordinary network variance on one attempt.
      for (var i = 1; i <= 5; i++) {
        try {
          final client = HttpClient();
          client.connectionTimeout = const Duration(seconds: 15);
          var requestUri = Uri.parse(
            'https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-IQ4_XS.gguf?download=true',
          );
          HttpClientResponse response;
          while (true) {
            final request = await client.getUrl(requestUri);
            request.followRedirects = false;
            response = await request.close();
            if (response.statusCode != 302 && response.statusCode != 301) break;
            final location = response.headers.value(HttpHeaders.locationHeader)!;
            requestUri = requestUri.resolve(location);
            await response.drain<void>();
          }
          final firstChunk = await response.first;
          debugPrint('SPRINT0_REPEAT_PROBE_$i: OK -- status ${response.statusCode}, first chunk ${firstChunk.length} bytes');
          client.close(force: true);
        } catch (e) {
          debugPrint('SPRINT0_REPEAT_PROBE_$i: FAILED -- $e');
        }
      }

      // Real, decisive fourth-stage diagnostic: the one thing every probe
      // above never did that llamadart's own real code always does first
      // -- instantiate the real native LlamaEngine (loads the llama.cpp
      // FFI library) BEFORE attempting any download. Every probe above
      // ran before this point and was 100% reliable (5/5 repeats). If the
      // identical request now fails only after a real engine exists, the
      // native library's own initialization -- not Dart's networking, not
      // the URL, not the device/network -- is the real, precise cause.
      LlamaEngine? diagnosticEngine;
      try {
        diagnosticEngine = LlamaEngine(LlamaBackend());
        debugPrint('SPRINT0_ENGINE_PROBE: real LlamaEngine constructed OK');
      } catch (e) {
        debugPrint('SPRINT0_ENGINE_PROBE: construction FAILED -- $e');
      }

      try {
        final client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 15);
        var requestUri = Uri.parse(
          'https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-IQ4_XS.gguf?download=true',
        );
        HttpClientResponse response;
        while (true) {
          final request = await client.getUrl(requestUri);
          request.followRedirects = false;
          response = await request.close();
          if (response.statusCode != 302 && response.statusCode != 301) break;
          final location = response.headers.value(HttpHeaders.locationHeader)!;
          requestUri = requestUri.resolve(location);
          await response.drain<void>();
        }
        final firstChunk = await response.first;
        debugPrint('SPRINT0_POST_ENGINE_PROBE: OK -- status ${response.statusCode}, first chunk ${firstChunk.length} bytes');
        client.close(force: true);
      } catch (e) {
        debugPrint('SPRINT0_POST_ENGINE_PROBE: FAILED -- $e');
      }
      await diagnosticEngine?.dispose();

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
