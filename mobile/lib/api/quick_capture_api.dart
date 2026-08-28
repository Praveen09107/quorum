/// The real, live `POST /quick_capture` implementation (`DEC-153`).
/// Matches every other real fetcher's established injected-function
/// pattern exactly (`trust_digest_api.dart`'s own header comment has the
/// full account of why: a plain injected async function, real client
/// ownership, a fresh access token per call).
///
/// A real, honest `503`/`502` distinction preserved from the backend:
/// `503` means the extraction provider isn't configured at all (a real
/// deployment/config problem); `502` means a real extraction attempt was
/// made and genuinely failed (a transient Gemini failure, or free text
/// that couldn't honestly be turned into a task) -- surfaced as two
/// different real messages, never collapsed into one generic failure.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/quick_capture/quick_capture_logic.dart';

Future<QuickCaptureResultData> Function(String text) createQuickCaptureFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String text) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/quick_capture'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 422) {
      throw const ApiException('Type something first.', statusCode: 422);
    }
    if (response.statusCode == 503) {
      throw const ApiException('Quick capture is not currently available.', statusCode: 503);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? "Couldn't turn that into a real task -- try rephrasing it.", statusCode: 502);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not submit that right now.', statusCode: response.statusCode);
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseQuickCaptureResult(json);
  };
}

String? _tryParseDetail(String body) {
  try {
    final json = jsonDecode(body) as Map<String, dynamic>;
    return json['detail'] as String?;
  } catch (e) {
    return null;
  }
}

QuickCaptureResultData _parseQuickCaptureResult(Map<String, dynamic> json) {
  final findingsJson = json['findings'] as List<dynamic>;
  return QuickCaptureResultData(
    executed: json['executed'] as bool,
    decision: json['decision'] as String,
    stakes: json['stakes'] as String,
    title: json['title'] as String?,
    findings: [
      for (final findingJson in findingsJson)
        FindingSummary(
          validator: (findingJson as Map<String, dynamic>)['validator'] as String,
          claim: findingJson['claim'] as String,
          visualState: visualStateForEvidence(findingJson['evidence_state'] as String),
        ),
    ],
  );
}
