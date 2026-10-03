/// The real, live task-completion/cancellation fetchers -- closes a
/// real, previously-undiscovered gap: `tasks_screen.dart`'s own
/// trailing status `Chip` has looked like a button since it was
/// written, but no real backend route anywhere has ever let a real,
/// signed-in user actually mark a task done or cancelled. Matches
/// `action_approval_api.dart`'s own established parameterized-fetcher
/// pattern exactly.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

typedef CompleteTaskCall = Future<void> Function(String taskId);
typedef CancelTaskCall = Future<void> Function(String taskId);

String? _tryParseDetail(String body) {
  try {
    final json = jsonDecode(body) as Map<String, dynamic>;
    return json['detail'] as String?;
  } catch (e) {
    return null;
  }
}

CompleteTaskCall createCompleteTaskFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String taskId) => _postTaskTransition(
        getAccessToken: getAccessToken,
        client: client,
        baseUrl: baseUrl,
        taskId: taskId,
        action: 'complete',
      );
}

CancelTaskCall createCancelTaskFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String taskId) => _postTaskTransition(
        getAccessToken: getAccessToken,
        client: client,
        baseUrl: baseUrl,
        taskId: taskId,
        action: 'cancel',
      );
}

Future<void> _postTaskTransition({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  required String baseUrl,
  required String taskId,
  required String action,
}) async {
  final accessToken = await getAccessToken();
  if (accessToken == null) {
    throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
  }

  final http.Response response;
  try {
    response = await client.post(
      Uri.parse('$baseUrl/tasks/${Uri.encodeComponent(taskId)}/$action'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
  } catch (e) {
    throw const ApiException('Could not reach Quorum -- check your connection and try again.');
  }

  if (response.statusCode == 200) return;
  if (response.statusCode == 401) {
    throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
  }
  if (response.statusCode == 404) {
    throw const ApiException('This task could not be found.', statusCode: 404);
  }
  if (response.statusCode == 409) {
    final detail = _tryParseDetail(response.body);
    throw ApiException(detail ?? 'This task is no longer open.', statusCode: 409);
  }
  throw ApiException('Could not update this task right now.', statusCode: response.statusCode);
}
