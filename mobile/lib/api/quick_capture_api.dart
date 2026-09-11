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

/// REAL, DISCLOSED, `QUORUM_FINAL_COMPLETION_PLAN.md` SESSION 8: this
/// fetcher's own returned function gained two new, optional, named
/// parameters -- `onDeviceAttempted`/`onDeviceFailureReason`, matching
/// the real backend's own new `QuickCaptureRequest` fields exactly. Every
/// existing real caller keeps working unchanged (both default to their
/// original, implicit "no on-device attempt happened" values); the new
/// real caller is `quick_capture_router.dart::routeQuickCapture()`'s own
/// cloud-fallback path, which always supplies a real, honest reason.
Future<QuickCaptureResultData> Function(String text, {bool onDeviceAttempted, String? onDeviceFailureReason}) createQuickCaptureFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String text, {bool onDeviceAttempted = false, String? onDeviceFailureReason}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/quick_capture'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'text': text,
          'on_device_attempted': onDeviceAttempted,
          'on_device_failure_reason': onDeviceFailureReason,
        }),
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

    // RESOLVED, a real, disclosed CRITICAL-tier review LOW (`DEC-153`
    // L5): `_parseQuickCaptureResult()`'s own real field casts previously
    // ran OUTSIDE this try/catch -- a real `200` response missing an
    // expected key would have thrown a raw, uncaught type-cast error
    // instead of the same honest `ApiException` every other malformed-
    // response case here already produces. Both steps are now inside
    // one real try/catch.
    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return _parseQuickCaptureResult(json);
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}

/// REAL, NEW -- `QUORUM_FINAL_COMPLETION_PLAN.md` SESSION 8. The real
/// `POST /quick_capture/extracted` fetcher: submits an already-extracted
/// args map (from a real, on-device extraction pass that already cleared
/// `on_device_correctness.dart`'s own bar) directly, skipping the real
/// cloud extraction call entirely. Real response parsing and real
/// `401`/`422`/`502` handling mirror [createQuickCaptureFetcher] above
/// exactly -- see that function's own header comment for the full
/// account; the two real routes share a byte-for-byte identical response
/// shape by construction (`main.py::_quick_capture_result_to_dict()`).
Future<QuickCaptureResultData> Function(Map<String, dynamic> args) createQuickCaptureExtractedFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (Map<String, dynamic> args) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/quick_capture/extracted'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode(args),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 422) {
      throw const ApiException('That could not be turned into a real action.', statusCode: 422);
    }
    if (response.statusCode == 503) {
      throw const ApiException('Quick capture is not currently available.', statusCode: 503);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? "Couldn't turn that into a real action -- try rephrasing it.", statusCode: 502);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not submit that right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return _parseQuickCaptureResult(json);
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
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
    // REAL, DISCLOSED SESSION-4/5/6 EXTENSION: `domain`/`operation` are
    // always present in the real backend response (`QUORUM_DATA_
    // CONTRACTS.md` §5.18); `amount`/`category`/`payee`/`finance_action`
    // are the real `finance`-domain fields, `event_start`/`event_end`/
    // `event_title`/`calendar_action` the real `calendar`-domain ones,
    // `company`/`new_status` the real `career`-domain ones -- all
    // always present but `null` for a non-matching domain's result
    // (`calendar_action`/`company`/`new_status`, and `payee`/`amount`/
    // `finance_action`/`title` for a genuine `update`/`delete`, are the
    // real exceptions populated regardless of `executed` -- see
    // `QuickCaptureResultData`'s own docstring for why).
    domain: json['domain'] as String,
    operation: json['operation'] as String?,
    title: json['title'] as String?,
    amount: (json['amount'] as num?)?.toDouble(),
    category: json['category'] as String?,
    payee: json['payee'] as String?,
    financeAction: json['finance_action'] as String?,
    eventStart: json['event_start'] as String?,
    eventEnd: json['event_end'] as String?,
    eventTitle: json['event_title'] as String?,
    calendarAction: json['calendar_action'] as String?,
    company: json['company'] as String?,
    newStatus: json['new_status'] as String?,
    // REAL, DISCLOSED SESSION-7 EXTENSION: `email_recipient`/`email_
    // action` are the fifth, final real domain's own fields -- see
    // `QuickCaptureResultData`'s own docstring for the real, considered
    // "only when genuinely executed"/"regardless of executed" split.
    emailRecipient: json['email_recipient'] as String?,
    emailAction: json['email_action'] as String?,
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
