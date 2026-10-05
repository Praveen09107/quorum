/// The real, live `POST /capture/stream` client (`DEC-189` Block B).
///
/// Returns a `Stream<GateEvent>` rather than a `Future<Result>` --
/// that is the whole point of this route and the reason it exists
/// alongside `quick_capture_api.dart` rather than replacing it. The
/// ordinary `POST /quick_capture` fetcher is still correct for any
/// caller that just wants the answer (the home-screen widget, the
/// share-sheet handler); this one is for the screen that shows the Gate
/// working.
///
/// WHY `client.send()` AND NOT `client.post()`: `http.Client.post()`
/// buffers the entire response body before returning it, which would
/// collect every event and hand them over at once -- producing exactly
/// the "renders a finished verdict" behaviour this feature exists to
/// replace, while appearing to work. `send()` returns a
/// `StreamedResponse` whose `.stream` yields bytes as they genuinely
/// arrive.
library;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_pipeline/gate_pipeline_logic.dart';

/// The signature a screen depends on. A function type, not a class,
/// matching every other API client in this app -- so a widget test
/// injects a plain closure yielding canned events and never touches
/// HTTP, which is the same "injected dependency at every real/external
/// boundary" pattern the rest of this project uses.
typedef CaptureStreamFetcher = Stream<GateEvent> Function(
  String text, {
  bool onDeviceAttempted,
  String? onDeviceFailureReason,
});

CaptureStreamFetcher createCaptureStreamFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String text, {bool onDeviceAttempted = false, String? onDeviceFailureReason}) {
    // An async generator, so the whole body runs lazily when the stream
    // is listened to -- and crucially so a `yield` reaches the UI the
    // moment a frame is parsed rather than after the response ends.
    return _streamCapture(
      text: text,
      onDeviceAttempted: onDeviceAttempted,
      onDeviceFailureReason: onDeviceFailureReason,
      getAccessToken: getAccessToken,
      client: client,
      baseUrl: baseUrl,
    );
  };
}

Stream<GateEvent> _streamCapture({
  required String text,
  required bool onDeviceAttempted,
  required String? onDeviceFailureReason,
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  required String baseUrl,
}) async* {
  final accessToken = await getAccessToken();
  if (accessToken == null) {
    throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
  }

  final request = http.Request('POST', Uri.parse('$baseUrl/capture/stream'))
    ..headers.addAll({
      'Authorization': 'Bearer $accessToken',
      'Content-Type': 'application/json',
      // Declares what this client actually understands. The server sets
      // the content type regardless, but sending this makes a
      // misconfigured proxy that rewrites the response type visible as a
      // real mismatch rather than a silently empty stream.
      'Accept': 'text/event-stream',
    })
    ..body = jsonEncode({
      'text': text,
      'on_device_attempted': onDeviceAttempted,
      'on_device_failure_reason': onDeviceFailureReason,
    });

  final http.StreamedResponse response;
  try {
    response = await client.send(request);
  } catch (_) {
    throw const ApiException('Could not reach Quorum -- check your connection and try again.');
  }

  // Every precondition the server can check before streaming begins
  // comes back as a real HTTP status, because the route deliberately
  // validates auth, the user and provider configuration BEFORE
  // constructing its streaming response. So these are genuine statuses
  // here, not in-band errors.
  if (response.statusCode != 200) {
    final body = await response.stream.bytesToString();
    throw ApiException(_messageForStatus(response.statusCode, body), statusCode: response.statusCode);
  }

  final parser = SseFrameParser();
  // `utf8.decoder` over the byte stream rather than decoding each chunk
  // independently: a multi-byte character can genuinely straddle a chunk
  // boundary, and per-chunk decoding would corrupt it. The converter
  // holds that state correctly.
  final lines = response.stream.transform(utf8.decoder);

  await for (final chunk in lines) {
    for (final payload in parser.addChunk(chunk)) {
      final GateEvent event;
      try {
        event = GateEvent.fromJson(payload);
      } on FormatException {
        // A malformed frame is a real protocol error, but dropping one
        // frame is strictly better than aborting a capture that is
        // already running server-side and will commit regardless. The
        // pipeline view will show the affected step as never having
        // reported, which is honest.
        continue;
      }
      yield event;
    }
  }
}

String _messageForStatus(int status, String body) {
  // Prefers the server's own `detail` when there is one -- it is
  // written for a user and says something specific, which is strictly
  // more useful than a generic message chosen by status code alone.
  final detail = _tryParseDetail(body);
  return switch (status) {
    401 => 'Your session has expired -- please sign in again.',
    422 => 'Type something first.',
    503 => detail ?? 'Quick capture is not currently available right now.',
    502 => detail ?? "Couldn't turn that into a real action -- try rephrasing it.",
    _ => detail ?? 'Could not submit that right now.',
  };
}

String? _tryParseDetail(String body) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
    }
  } catch (_) {
    // A non-JSON error body is genuinely possible from a proxy rather
    // than from this backend -- fall back to the status-based message.
  }
  return null;
}
