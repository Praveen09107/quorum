/// The real, live `GateRevealFetcher` implementation. Matches
/// `negotiation_api.dart`'s own established parameterized-fetcher
/// pattern exactly: a plain injected async function taking the real
/// id it needs, a fresh access token read on every request, the same
/// `ApiException` error taxonomy.
///
/// Calls the real, live `GET /gate_reveal/{proposal_id}` (Phase 6,
/// `features/gate_reveal.py`) -- closes the real, disclosed gap
/// `DEC-126` found: `gate_reveal_logic.dart`/`gate_reveal_screen.dart`
/// have existed since Batch 6 (`DEC-080`), and `main_shell.dart`'s own
/// `_TodayTab` already wires a real tap-through from a "Needs you now"
/// card, but no real backend ever existed for either to call.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

Future<GateRevealBundle> Function(String proposalId) createGateRevealFetcher({
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
        Uri.parse('$baseUrl/gate_reveal/$proposalId'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode == 404) {
      throw const ApiException('This action could not be found.', statusCode: 404);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not load why Quorum is asking about this right now.',
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
      return GateRevealBundle(
        findings: (json['findings'] as List<dynamic>).map((raw) => _parseFinding(raw as Map<String, dynamic>)).toList(),
        objections: (json['objections'] as List<dynamic>).map((raw) => _parseObjection(raw as Map<String, dynamic>)).toList(),
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}

FindingSummary _parseFinding(Map<String, dynamic> json) {
  return FindingSummary(
    validator: json['validator'] as String,
    claim: json['claim'] as String,
    visualState: visualStateForEvidence(json['evidence_state'] as String),
  );
}

ObjectionSummary _parseObjection(Map<String, dynamic> json) {
  return ObjectionSummary(
    category: json['category'] as String,
    severity: json['severity'] as String,
    description: json['description'] as String,
    signedOff: json['signed_off'] as bool,
  );
}
