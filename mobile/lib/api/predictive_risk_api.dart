/// The real, live `PredictiveRiskFetcher` implementation. Matches
/// `career_digest_api.dart`/`tasks_api.dart`'s own established
/// no-parameter-fetcher pattern -- a plain injected async function, a
/// fresh access token read on every request, the same `ApiException`
/// error taxonomy.
///
/// Calls the real, live `GET /predictive_risk` (Phase 6,
/// `features/predictive_risk.py`) -- see that module's own top-of-file
/// docstring for the real, disclosed design decisions this feature's
/// backend made where no prior spec contract existed. Every field name
/// below was checked directly against that route's own real response
/// shape before writing this file, not assumed.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';

Future<RiskAssessmentData> Function() createPredictiveRiskFetcher({
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
        Uri.parse('$baseUrl/predictive_risk'),
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
        "Could not load next week's predicted risk right now.",
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
      return RiskAssessmentData(
        weekStart: DateTime.parse(json['week_start'] as String),
        deadlineDensity: json['deadline_density'] as int,
        matchingHistoricalWeeks: json['matching_historical_weeks'] as int,
        pooledCorrectionRate: (json['pooled_correction_rate'] as num?)?.toDouble(),
        isAtRisk: json['is_at_risk'] as bool,
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
