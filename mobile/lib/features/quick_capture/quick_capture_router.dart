// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies (deliberately does NOT import
// `on_device_extraction.dart`, which pulls in the real `llamadart` native
// plugin -- every dependency here is injected instead, matching this
// project's own established DI convention) -- `dart test` is the real
// verification.
//
// `QUORUM_FINAL_COMPLETION_PLAN.md` Session 8's own real orchestration:
// given a real, on-device-first extraction attempt and a real,
// structural correctness bar (`on_device_correctness.dart`), decide
// whether to submit the trusted, already-extracted result directly (`POST
// /quick_capture/extracted`, skipping the real cloud extraction entirely)
// or fall back to the existing real cloud path (`POST /quick_capture`),
// honestly reporting the real fallback and its real reason -- this
// session's own stated "every fallback is logged, not silent"
// requirement, satisfied end to end: this file supplies the real reason
// string, `quick_capture_api.dart`'s extended `createQuickCaptureFetcher`
// carries it to the backend, and the backend's own new log line
// (`main.py`) makes it real, durable, and observable.
//
// A REAL, DELIBERATE SAFETY FACT: a real failure from the TRUSTED,
// already-extracted submission (`submitExtracted` below) is never
// silently retried via the cloud path -- an honest `502`/`503` from the
// real Gate reviewing a genuinely-correct extraction is a real, honest
// outcome of that specific submission, not a signal the extraction
// itself was wrong. Silently resubmitting via cloud on ANY failure would
// risk a real, duplicate action reaching the Gate twice for one real
// user intent -- this router only ever falls back BEFORE submission,
// based on the real correctness bar alone, exactly matching this
// session's own spec text ("falling back to the real cloud path whenever
// the on-device result is missing, malformed, or below a real,
// deliberately-conservative confidence bar").

import 'package:quorum_mobile/features/quick_capture/on_device_correctness.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';

/// Matches `on_device_extraction.dart`'s own real `OnDeviceExtractionCall`
/// typedef shape exactly, redeclared here (rather than imported) so this
/// file stays genuinely free of any dependency on `package:llamadart` --
/// a real, deliberate choice, not an oversight; the two typedefs are
/// structurally identical by construction and Dart's own structural
/// typing means a real `extractWithOnDeviceModel` value satisfies this
/// one without either file importing the other.
typedef OnDeviceExtractCall = Future<Map<String, dynamic>> Function(String freeText);

/// A real, already-extracted-args submission -- the real
/// `POST /quick_capture/extracted` fetcher.
typedef ExtractedSubmitCall = Future<QuickCaptureResultData> Function(Map<String, dynamic> args);

/// A real, free-text cloud-fallback submission -- the real, EXISTING
/// `POST /quick_capture` fetcher, extended this session with the real
/// fallback-telemetry fields.
typedef CloudSubmitCall = Future<QuickCaptureResultData> Function(
  String freeText, {
  required bool onDeviceAttempted,
  String? onDeviceFailureReason,
});

/// THE real, single entry point every Quick-capture UI call site should
/// route through from this session forward, replacing a bare
/// `createQuickCaptureFetcher()` call with this real, on-device-first
/// decision. Never throws anything other than what [submitExtracted]/
/// [submitCloud] themselves throw -- a real on-device failure (model
/// load, inference, or a response that doesn't parse) is always caught
/// here and always routed to the real cloud path instead, never
/// surfaced to the user as its own error.
Future<QuickCaptureResultData> routeQuickCapture(
  String freeText, {
  required OnDeviceExtractCall onDeviceExtract,
  required ExtractedSubmitCall submitExtracted,
  required CloudSubmitCall submitCloud,
}) async {
  Map<String, dynamic> args;
  try {
    args = await onDeviceExtract(freeText);
  } catch (e) {
    return submitCloud(freeText, onDeviceAttempted: true, onDeviceFailureReason: 'on-device extraction failed: $e');
  }

  final check = checkOnDeviceExtraction(args);
  if (!check.passed) {
    return submitCloud(freeText, onDeviceAttempted: true, onDeviceFailureReason: check.reason);
  }

  // A real, deliberate choice: a genuine failure of the TRUSTED
  // submission itself (the real Gate/backend rejecting an
  // already-correct-looking extraction) propagates directly -- see this
  // file's own header comment for why silently retrying via cloud here
  // would be unsafe, not merely redundant.
  return submitExtracted(args);
}
