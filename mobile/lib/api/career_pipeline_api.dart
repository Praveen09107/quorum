/// The real, live `CareerFetcher` implementation. Matches
/// `tasks_api.dart`/`trust_api.dart`'s already-established pattern
/// exactly: a plain injected async function, a fresh access token read
/// on every request, the same `ApiException` error taxonomy.
///
/// Calls the real, live `GET /career_pipeline` -- queries the real
/// `applications` table directly (`features/career_pipeline.py`). Same
/// real, disclosed limitation as `/trust_digest`/`/tasks`: no
/// per-user filtering yet, since no real user-provisioning system maps
/// a Google identity onto `applications.user_id` anywhere in this
/// backend -- this is a real "you must be signed in" gate, not yet a
/// per-user data filter.
///
/// A real, deliberate CONTRAST with `tasks_api.dart`: `status` here is
/// a plain `String`, never parsed through a closed-set enum parser --
/// `applications.status` has no real database `CHECK` constraint
/// (confirmed against the real migration before writing this file),
/// so any value the server sends is passed through unchanged, exactly
/// matching `career_pipeline_logic.dart`'s own already-tested
/// defensive handling (`statusLabel()`'s de-snaking fallback,
/// `groupByStatus()`'s never-drop-an-unrecognized-status behavior).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/career/career_pipeline_logic.dart';

Future<List<CareerApplication>> Function() createCareerPipelineFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return () async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/career_pipeline'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not load your career pipeline right now.',
        statusCode: response.statusCode,
      );
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return json.map((raw) => _parseApplication(raw as Map<String, dynamic>)).toList();
  };
}

CareerApplication _parseApplication(Map<String, dynamic> json) {
  final deadlineRaw = json['deadline'] as String?;
  return CareerApplication(
    applicationId: json['application_id'] as String,
    company: json['company'] as String,
    role: json['role'] as String?,
    // A real, open vocabulary -- never parsed through a closed-set enum,
    // passed through exactly as the server sent it.
    status: json['status'] as String,
    deadline: deadlineRaw == null ? null : DateTime.parse(deadlineRaw),
  );
}
