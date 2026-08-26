/// The real, live `HonestyFeedFetcher` implementation. Matches
/// `waiting_on_api.dart`/`career_pipeline_api.dart`'s already-
/// established pattern exactly: a plain injected async function, a
/// fresh access token read on every request, the same `ApiException`
/// error taxonomy.
///
/// Calls the real, live `GET /honesty_log` (Phase 6, `features/
/// honesty_log.py`) -- closes the real, permanently-dead "Log"
/// bottom-nav tab for the first time since `honesty_log_logic.dart`/
/// `honesty_log_screen.dart` were built years ahead of any real
/// backend to call (Batch 8, `DEC-087`).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

Future<HonestyFeedData> Function() createHonestyLogFetcher({
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
        Uri.parse('$baseUrl/honesty_log'),
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
        'Could not load your honesty log right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    try {
      return HonestyFeedData(
        total: json['total'] as int,
        successRate: json['success_rate'] == null ? null : (json['success_rate'] as num).toDouble(),
        successes: _parseActions(json['successes']),
        failuresAndCatches: _parseActions(json['failures_and_catches']),
        genuinelyUncertain: _parseActions(json['genuinely_uncertain']),
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}

List<LoggedActionData> _parseActions(dynamic rawList) {
  return (rawList as List<dynamic>).map((raw) {
    final item = raw as Map<String, dynamic>;
    return LoggedActionData(
      actionId: item['action_id'] as String,
      timestamp: DateTime.parse(item['timestamp'] as String),
      outcome: item['outcome'] as String,
      description: item['description'] as String,
    );
  }).toList();
}
