/// The real, live `TrustFetcher` implementation. Matches
/// `trust_digest_api.dart`'s already-established pattern exactly: a
/// plain injected async function (never an invented `Repository`
/// class), a fresh access token read on every request (never a stale
/// captured value), and the same real/network-failure/malformed-body
/// error taxonomy via `ApiException`.
///
/// Calls the real, live `GET /trust` -- runs the real adversarial
/// scenario suite directly against the real `gate.review()`
/// (`self_test_harness.py`, `DEC-099`; wired to a real HTTP route this
/// session). Unlike `/trust_digest`, this endpoint has no live-database
/// dependency of its own -- the real Gate scenarios run entirely
/// in-memory -- but still requires a real, valid access token, matching
/// this project's standing "every endpoint touching real verification
/// data requires sign-in" pattern.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/trust/trust_logic.dart';

Future<TrustData> Function() createTrustFetcher({
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
        Uri.parse('$baseUrl/trust'),
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
        'Could not load your trust self-test results right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseTrustData(json);
  };
}

TrustData _parseTrustData(Map<String, dynamic> json) {
  final missed = (json['missed'] as List<dynamic>)
      .map((raw) => _parseScenarioResult(raw as Map<String, dynamic>))
      .toList();
  final results = (json['results'] as List<dynamic>)
      .map((raw) => _parseScenarioResult(raw as Map<String, dynamic>))
      .toList();
  return TrustData(
    total: json['total'] as int,
    caught: json['caught'] as int,
    missed: missed,
    results: results,
    // Reuses the existing, already-tested parseTarget() exactly -- the
    // same fail-closed-to-stub discipline, never re-derived here.
    target: parseTarget(json['target'] as String),
  );
}

ScenarioResultData _parseScenarioResult(Map<String, dynamic> json) {
  return ScenarioResultData(
    scenarioId: json['scenario_id'] as String,
    expected: json['expected'] as String,
    actual: json['actual'] as String,
    passed: json['passed'] as bool,
  );
}
