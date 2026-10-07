/// The real, live `PUT /tasks/{task_id}` fetcher (`DEC-214`, product
/// rebuild Part C). Matches `create_task_api.dart`'s own established
/// pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_verdict/gate_verdict_parsing.dart';

/// A real, honest, minimal summary of what happened.
class UpdateTaskResult {
  final bool executed;
  final String decision;
  final String stakes;
  final String? title;
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const UpdateTaskResult({
    required this.executed,
    required this.decision,
    required this.stakes,
    this.title,
    this.findings = const [],
    this.objections = const [],
  });
}

typedef UpdateTaskFetcher = Future<UpdateTaskResult> Function({
  required String taskId,
  String? title,
  double? estimatedHours,
  DateTime? deadline,
});

UpdateTaskFetcher createUpdateTaskFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String taskId, String? title, double? estimatedHours, DateTime? deadline}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.put(
        Uri.parse('$baseUrl/tasks/$taskId'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          if (title != null) 'title': title,
          if (estimatedHours != null) 'estimated_hours': estimatedHours,
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
      throw ApiException(detail ?? "Couldn't update that task -- try again.", statusCode: 502);
    }
    if (response.statusCode == 503) {
      throw const ApiException('The Gate\'s reviewer is temporarily unavailable -- please try again shortly.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not update that task right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return UpdateTaskResult(
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
