/// The real, live `NegotiationFetcher` implementation. Matches
/// `today_api.dart`/`search_api.dart`'s already-established pattern
/// exactly: a plain injected async function, a fresh access token read
/// on every request, the same `ApiException` error taxonomy.
///
/// Calls the real, live `GET /negotiations/{id}` (`features/
/// negotiation_detail.py`) -- a real gap found and closed the same
/// session as the demo dataset work: `NegotiationBundle` has existed as
/// a real, tested type since `MOBILE_09`, but no real backend contract
/// or wiring for it ever existed until now.
///
/// `createChooseNegotiationFetcher` calls the real, live `POST
/// /negotiations/{id}/choose` (`features/negotiation_choice.py`),
/// closing the gap `DEC-104`/`DEC-121` both disclosed: a person could
/// see a real negotiation's real positions/options but never act on
/// one. `409`/`400` map to distinct, real `ApiException`s -- "already
/// resolved" and "not a real option" are genuinely different failures
/// a real UI should be able to tell apart, not collapsed into one
/// generic error.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';

Future<NegotiationBundle> Function(String negotiationId) createNegotiationFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String negotiationId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/negotiations/$negotiationId'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('This negotiation could not be found.', statusCode: 404);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not load this negotiation right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseNegotiationBundle(json);
  };
}

Future<void> Function(String negotiationId, String optionId) createChooseNegotiationFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String negotiationId, String optionId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.post(
        Uri.parse('$baseUrl/negotiations/$negotiationId/choose'),
        headers: {'Authorization': 'Bearer $accessToken', 'Content-Type': 'application/json'},
        body: jsonEncode({'chosen_option': optionId}),
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 202) return;

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('This negotiation could not be found.', statusCode: 404);
    }
    if (response.statusCode == 400) {
      throw const ApiException('That is not one of this negotiation\'s real options.', statusCode: 400);
    }
    if (response.statusCode == 409) {
      throw const ApiException('This negotiation already has a chosen option.', statusCode: 409);
    }
    throw ApiException('Could not submit your choice right now.', statusCode: response.statusCode);
  };
}

PositionData _parsePosition(Map<String, dynamic> json) {
  return PositionData(
    domain: json['domain'] as String,
    concern: json['concern'] as String,
    proposedResolution: json['proposed_resolution'] as String,
  );
}

ImpactDeltaData _parseImpactDelta(Map<String, dynamic> json) {
  return ImpactDeltaData(
    metric: json['metric'] as String,
    before: (json['before'] as num).toDouble(),
    after: (json['after'] as num).toDouble(),
    direction: json['direction'] as String,
  );
}

NegotiationOptionData _parseOption(Map<String, dynamic> json) {
  return NegotiationOptionData(
    optionId: json['option_id'] as String,
    description: json['description'] as String,
    sourceDomains: (json['source_domains'] as List<dynamic>).cast<String>(),
    impact: (json['impact'] as List<dynamic>).map((raw) => _parseImpactDelta(raw as Map<String, dynamic>)).toList(),
  );
}

NegotiationBundle _parseNegotiationBundle(Map<String, dynamic> json) {
  final positions = (json['positions'] as List<dynamic>).map((raw) => _parsePosition(raw as Map<String, dynamic>)).toList();
  final options = (json['options'] as List<dynamic>).map((raw) => _parseOption(raw as Map<String, dynamic>)).toList();
  return NegotiationBundle(positions: positions, options: options);
}
