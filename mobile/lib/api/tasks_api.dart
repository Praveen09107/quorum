/// The real, live `TaskListFetcher` implementation. Matches
/// `trust_api.dart`/`trust_digest_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error
/// taxonomy.
///
/// Calls the real, live `GET /tasks` -- queries the real `tasks` table
/// directly (`features/tasks.py`). Same real, disclosed limitation as
/// `/trust_digest`: no per-user filtering yet, since no real
/// user-provisioning system maps a Google identity onto `tasks.user_id`
/// anywhere in this backend -- this is a real "you must be signed in"
/// gate, not yet a per-user data filter.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';

Future<List<TaskData>> Function() createTasksFetcher({
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
        Uri.parse('$baseUrl/tasks'),
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
        'Could not load your tasks right now.',
        statusCode: response.statusCode,
      );
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    // Deliberately outside the try/catch above -- the same real
    // convention `trust_digest_api.dart`/`trust_api.dart` already
    // establish: a syntactically valid JSON body that fails to parse
    // semantically (e.g. `parseTaskStatus` rejecting a genuinely
    // unrecognized value, per `tasks.status`'s own closed-set, fail-loud
    // contract) is a real schema-drift bug, surfaced as-is, never
    // smoothed over into a generic ApiException.
    return json.map((raw) => _parseTask(raw as Map<String, dynamic>)).toList();
  };
}

TaskData _parseTask(Map<String, dynamic> json) {
  final deadlineRaw = json['deadline'] as String?;
  return TaskData(
    taskId: json['task_id'] as String,
    title: json['title'] as String,
    estimatedHours: (json['estimated_hours'] as num).toDouble(),
    deadline: deadlineRaw == null ? null : DateTime.parse(deadlineRaw),
    status: parseTaskStatus(json['status'] as String),
  );
}
