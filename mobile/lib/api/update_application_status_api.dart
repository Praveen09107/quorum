/// The real, live `PUT /applications/{application_id}/status` fetcher
/// (`DEC-216`/`DEC-218`, product rebuild Part C, Priority 2 completion).
/// Matches `update_task_api.dart`'s own established pattern exactly --
/// direct-by-id, no narrated-reference resolution, since a mobile
/// client editing a row it's already looking at already has the real
/// application id.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_verdict/gate_verdict_parsing.dart';

/// A real, honest, minimal summary of what happened.
class UpdateApplicationStatusResult {
  final bool executed;
  final String decision;
  final String stakes;
  final String? company;
  final String? newStatus;
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const UpdateApplicationStatusResult({
    required this.executed,
    required this.decision,
    required this.stakes,
    this.company,
    this.newStatus,
    this.findings = const [],
    this.objections = const [],
  });
}

typedef UpdateApplicationStatusFetcher = Future<UpdateApplicationStatusResult> Function({
  required String applicationId,
  required String newStatus,
});

UpdateApplicationStatusFetcher createUpdateApplicationStatusFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return ({required String applicationId, required String newStatus}) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.put(
        Uri.parse('$baseUrl/applications/$applicationId/status'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({'new_status': newStatus}),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 502) {
      final detail = _tryParseDetail(response.body);
      throw ApiException(detail ?? "Couldn't update that application's status -- try again.", statusCode: 502);
    }
    if (response.statusCode == 503) {
      throw const ApiException('The Gate\'s reviewer is temporarily unavailable -- please try again shortly.', statusCode: 503);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not update that application\'s status right now.', statusCode: response.statusCode);
    }

    try {
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return UpdateApplicationStatusResult(
        executed: json['executed'] as bool,
        decision: json['decision'] as String,
        stakes: json['stakes'] as String,
        company: json['company'] as String?,
        newStatus: json['new_status'] as String?,
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
