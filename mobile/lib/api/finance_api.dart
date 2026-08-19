/// The real, live `FinanceFetcher` implementation. Matches
/// `career_pipeline_api.dart`/`tasks_api.dart`'s already-established
/// pattern exactly: a plain injected async function, a fresh access
/// token read on every request, the same `ApiException` error
/// taxonomy.
///
/// Calls the real, live `GET /finance/subscriptions` -- queries the
/// real `expenses` table via `features/subscription_detective.py`'s
/// real, deliberately simple detection rule (a payee charged at least
/// twice, exact match only). Same real, disclosed limitation as
/// `/trust_digest`/`/tasks`/`/career_pipeline`: no per-user filtering
/// yet, since no real user-provisioning system maps a Google identity
/// onto `expenses.user_id` anywhere in this backend.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/finance/finance_logic.dart';

Future<List<DetectedSubscriptionData>> Function() createFinanceFetcher({
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
        Uri.parse('$baseUrl/finance/subscriptions'),
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
        'Could not load your subscriptions right now.',
        statusCode: response.statusCode,
      );
    }

    final List<dynamic> json;
    try {
      json = jsonDecode(response.body) as List<dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return json.map((raw) => _parseSubscription(raw as Map<String, dynamic>)).toList();
  };
}

DetectedSubscriptionData _parseSubscription(Map<String, dynamic> json) {
  return DetectedSubscriptionData(
    payee: json['payee'] as String,
    averageAmount: (json['average_amount'] as num).toDouble(),
    occurrences: json['occurrences'] as int,
    averageIntervalDays: (json['average_interval_days'] as num).toDouble(),
  );
}
