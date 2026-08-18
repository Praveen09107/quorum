/// The real, live `TrustDigestFetcher` implementation -- the first real
/// network-calling code in this mobile codebase's history. Matches
/// `shell/main_shell.dart`'s own established, disclosed pattern exactly:
/// a plain injected async function, not an invented `Repository` class
/// this project's real history never built.
///
/// Calls the real, live `GET /trust_digest` (`DEC-100`, `DEC-102`) --
/// backed by the real, live Supabase database, real auth-gated as of
/// `DEC-101`/`DEC-102`. `accessToken` is injected, never read from
/// storage here -- real secure token storage and the real Google
/// sign-in flow that produces it are separate, later, disclosed work
/// (no browser automation exists in this environment to build and
/// verify that end to end); this file's real job stops at "given a
/// valid token, make the real call and parse the real response."
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';

/// The return type is written out in full rather than via a private
/// typedef -- it matches `shell/main_shell.dart`'s own public
/// `TrustDigestFetcher` typedef structurally (Dart function types are
/// structural, not nominal, so no import of that typedef is needed),
/// and a private typedef in a public API's signature is exactly what
/// `flutter analyze` flags as `library_private_types_in_public_api`.
Future<TrustDigestData> Function() createTrustDigestFetcher({
  required String accessToken,
  http.Client? client,
  String baseUrl = ApiConfig.baseUrl,
}) {
  final httpClient = client ?? http.Client();

  return () async {
    final http.Response response;
    try {
      response = await httpClient.get(
        Uri.parse('$baseUrl/trust_digest'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
    } catch (e) {
      // A real network failure (no connectivity, DNS, timeout) --
      // statusCode stays null, honestly distinct from a real server
      // response that happened to be an error.
      throw const ApiException('Could not reach Quorum -- check your connection and try again.');
    }

    if (response.statusCode == 401) {
      throw const ApiException('Your session has expired -- please sign in again.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException(
        'Could not load your trust digest right now.',
        statusCode: response.statusCode,
      );
    }

    final Map<String, dynamic> json;
    try {
      json = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      // A real 200 with a body that isn't the shape this app expects --
      // a genuine backend/client contract mismatch, surfaced loudly,
      // never silently treated as "no data."
      throw const ApiException('Quorum sent back something this app could not understand.');
    }

    return _parseTrustDigest(json);
  };
}

TrustDigestData _parseTrustDigest(Map<String, dynamic> json) {
  final previousWeekJson = json['previous_week'] as Map<String, dynamic>?;
  return TrustDigestData(
    currentWeek: _parseWeek(json['current_week'] as Map<String, dynamic>),
    previousWeek: previousWeekJson == null ? null : _parseWeek(previousWeekJson),
    // Reuses the existing, already-tested parseTrend() exactly -- the
    // same fail-closed-to-insufficientData discipline, never re-derived.
    trend: parseTrend(json['trend'] as String),
    delta: (json['delta'] as num?)?.toDouble(),
  );
}

WeeklyTrustSummaryData _parseWeek(Map<String, dynamic> json) {
  return WeeklyTrustSummaryData(
    weekStart: json['week_start'] as String,
    totalActions: json['total_actions'] as int,
    successRate: (json['success_rate'] as num).toDouble(),
  );
}
