/// The real, live `POST /applications` fetcher (`DEC-194`, product
/// rebuild Block F). Matches `quick_capture_api.dart`'s own established
/// pattern -- a plain injected async function, a fresh access token per
/// call, the same real `401`/`502` taxonomy, since this route runs
/// through the identical real Gate pipeline under the hood.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

/// A real, honest, minimal summary of what happened -- `executed` is
/// the real fact a caller needs to decide whether to show "added" or a
/// genuine, if rare, Gate rejection. Mirrors `QuickCaptureResultData`'s
/// own established "closed, not open-ended" shape rather than passing
/// the raw response map through.
class CreateApplicationResult {
  final bool executed;
  final String decision;
  final String? company;

  const CreateApplicationResult({required this.executed, required this.decision, this.company});
}

typedef CreateApplicationFetcher = Future<CreateApplicationResult> Function({
  required String company,
  String? role,
  DateTime? deadline,
});

CreateApplicationFetcher createCreateApplicationFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String company, String? role, DateTime? deadline}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/applications'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'company': company,
          'role': role,
          'deadline_iso': deadline?.toUtc().toIso8601String(),
        }),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? "Couldn't add that application -- try again.", statusCode: 502);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not add that application right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return CreateApplicationResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        company: json['company'] as String?,
      );
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
