/// The real, live `CareerDigestFetcher` implementation. Matches
/// `gate_reveal_api.dart`/`negotiation_api.dart`'s own established
/// parameterized-fetcher pattern exactly: a plain injected async
/// function taking the real id it needs, a fresh access token read on
/// every request.
///
/// Calls the real, live `GET /career_pipeline/{application_id}/digest`
/// (Phase 6, `features/career_digest.py`) -- closes the real, disclosed
/// gap `career_digest_logic.dart`'s own header already named:
/// `you_screen.dart`'s own `_CareerDigestLoader` has existed since
/// Batch 7 (`DEC-084`), but no real backend ever existed for it to
/// call.
///
/// A REAL, DELIBERATE CONTRAST with every other fetcher in this
/// directory: a `404` here does NOT mean "error" -- it's the real,
/// honest, expected "not researched yet" state
/// (`career_digest_logic.dart`'s own `DigestNotYetAvailableException`),
/// so it is thrown as that specific, catchable type here, never
/// wrapped in the generic `ApiException` every other 404 in this
/// codebase uses.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';

Future<CompanyDigestData> Function(String applicationId) createCareerDigestFetcher({
  required Future<String?> Function() getAccessToken,
  required http.Client client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  return (String applicationId) async {
    final accessToken = await getAccessToken();
    if (accessToken == null) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }

    final http.Response response;
    try {
      response = await client.get(
        Uri.parse('$baseUrl/career_pipeline/${Uri.encodeComponent(applicationId)}/digest'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    // A real, honest, expected state -- not researched yet -- never the
    // generic ApiException the rest of this codebase's 404s use.
    if (response.statusCode == 404) {
      throw DigestNotYetAvailableException(applicationId);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        "Could not load this company's research digest right now.",
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
      return CompanyDigestData(
        company: json['company'] as String,
        summaryPoints: (json['summary_points'] as List<dynamic>).map((point) => point as String).toList(),
        sourceCount: json['source_count'] as int,
      );
    } catch (e) {
      throw const ApiException('Quorum sent back something this app could not understand.');
    }
  };
}
