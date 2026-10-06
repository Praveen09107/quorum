/// The real, live `POST /tasks` fetcher (`DEC-208`, product rebuild).
/// Matches `create_application_api.dart`'s own established pattern --
/// a plain injected async function, a fresh access token per call, the
/// same real `401`/`502`/`503` taxonomy, since this route runs through
/// the identical real Gate pipeline under the hood.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_verdict/gate_verdict_parsing.dart';

/// A real, honest, minimal summary of what happened -- `executed` is
/// the real fact a caller needs to decide whether to show "added" or a
/// genuine, if rare, Gate rejection. Mirrors `CreateApplicationResult`'s
/// own established "closed, not open-ended" shape.
///
/// `DEC-214`: `stakes`/`findings`/`objections` are the real Gate
/// verdict every response already carried but this result type
/// previously dropped.
class CreateTaskResult {
  final bool executed;
  final String decision;
  final String stakes;
  final String? title;
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const CreateTaskResult({
    required this.executed,
    required this.decision,
    required this.stakes,
    this.title,
    this.findings = const [],
    this.objections = const [],
  });
}

typedef CreateTaskFetcher = Future<CreateTaskResult> Function({
  required String title,
  required double estimatedHours,
  DateTime? deadline,
});

CreateTaskFetcher createCreateTaskFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String title, required double estimatedHours, DateTime? deadline}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/tasks'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'title': title,
          'estimated_hours': estimatedHours,
          if (deadline != null) 'deadline_iso': deadline.toUtc().toIso8601String(),
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
      throw ApiException(detail ?? "Couldn't add that task -- try again.", statusCode: 502);
    }
    if (response.statusCode == 503) {
      throw const ApiException('The Gate\'s reviewer is temporarily unavailable -- please try again shortly.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not add that task right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return CreateTaskResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        stakes: json['stakes'] as String,
        title: json['title'] as String?,
        findings: parseFindings(json['findings'] as List<dynamic>? ?? const []),
        objections: parseObjections(json['objections'] as List<dynamic>? ?? const []),
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
