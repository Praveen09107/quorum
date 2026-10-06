/// The real, live `POST /interviews` fetcher (`DEC-195`, product
/// rebuild Block F remainder). Matches `create_application_api.dart`'s
/// own established pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_verdict/gate_verdict_parsing.dart';

/// A real, honest, minimal summary of what happened.
///
/// `DEC-214`: `stakes`/`findings`/`objections` are the real Gate
/// verdict every response already carried but this result type
/// previously dropped.
class ScheduleInterviewResult {
  final bool executed;
  final String decision;
  final String stakes;
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const ScheduleInterviewResult({
    required this.executed,
    required this.decision,
    required this.stakes,
    this.findings = const [],
    this.objections = const [],
  });
}

typedef ScheduleInterviewFetcher = Future<ScheduleInterviewResult> Function({
  required String applicationId,
  DateTime? scheduledAt,
  String? format,
});

ScheduleInterviewFetcher createScheduleInterviewFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String applicationId, DateTime? scheduledAt, String? format}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/interviews'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'application_id': applicationId,
          'scheduled_at_iso': scheduledAt?.toUtc().toIso8601String(),
          'format': format,
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
      throw ApiException(detail ?? "Couldn't schedule that interview -- try again.", statusCode: 502);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not schedule that interview right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return ScheduleInterviewResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        stakes: json['stakes'] as String,
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
