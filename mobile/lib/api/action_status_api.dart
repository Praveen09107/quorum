/// The real, live fetcher for `GET /actions/{id}/status` (`DEC-189`
/// Block B, first real mobile caller `DEC-201`). Matches
/// `week_summary_api.dart`'s own established fetcher pattern, with one
/// real difference: the proposal id is a path parameter, not a fixed
/// URL, so this returns a function of it rather than a zero-argument
/// fetcher.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

/// Real, honest replay data for one past action. `timeline` is `null`
/// -- never an empty list -- for any real action resolved before
/// migration `0021` ever recorded one; an empty list would claim the
/// Gate ran zero checks, which would be false.
class ActionStatusData {
  final String proposalId;
  final String actionType;
  final String stakes;
  final String? gateDecision;
  final String? outcome;
  final DateTime? createdAt;
  final DateTime? resolvedAt;
  final Map<String, dynamic> payload;
  final List<dynamic>? timeline;
  final int? revisionCount;
  final Map<String, dynamic>? preRevisionPayload;
  final Map<String, dynamic>? artifact;

  const ActionStatusData({
    required this.proposalId,
    required this.actionType,
    required this.stakes,
    required this.gateDecision,
    required this.outcome,
    required this.createdAt,
    required this.resolvedAt,
    required this.payload,
    required this.timeline,
    required this.revisionCount,
    required this.preRevisionPayload,
    required this.artifact,
  });
}

typedef ActionStatusFetcher = Future<ActionStatusData> Function(String proposalId);

ActionStatusFetcher createActionStatusFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String proposalId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/actions/$proposalId/status'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('No such action was found.', statusCode: 404);
    }
    if (response.statusCode != 200) {
      throw ApiException('Could not load that action.', statusCode: response.statusCode);
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      return ActionStatusData(
        proposalId: json['proposal_id'] as String,
        actionType: json['action_type'] as String,
        stakes: json['stakes'] as String,
        gateDecision: json['gate_decision'] as String?,
        outcome: json['outcome'] as String?,
        createdAt: (json['created_at'] as String?) == null ? null : DateTime.parse(json['created_at'] as String),
        resolvedAt: (json['resolved_at'] as String?) == null ? null : DateTime.parse(json['resolved_at'] as String),
        payload: (json['payload'] as Map<String, dynamic>?) ?? const {},
        timeline: json['timeline'] as List<dynamic>?,
        revisionCount: json['revision_count'] as int?,
        preRevisionPayload: json['pre_revision_payload'] as Map<String, dynamic>?,
        artifact: json['artifact'] as Map<String, dynamic>?,
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
