/// The real, live `TrustDigestFetcher` implementation -- the first real
/// network-calling code in this mobile codebase's history. Matches
/// `shell/main_shell.dart`'s own established, disclosed pattern exactly:
/// a plain injected async function, not an invented `Repository` class
/// this project's real history never built.
///
/// Calls the real, live `GET /trust_digest` (`DEC-100`, `DEC-102`) --
/// backed by the real, live Supabase database, real auth-gated as of
/// `DEC-101`/`DEC-102`.
///
/// A real, disclosed correction from fresh-context review before this
/// merged: an earlier version created its own default `http.Client()`
/// when none was injected, silently owning a resource this module had
/// no way to ever close -- harmless while dormant (nothing called it
/// yet), but a real leak once actually wired up. `client` is now
/// required, never defaulted -- whoever wires this up for real owns
/// that client's lifecycle explicitly, the same "no hidden singleton,
/// every dependency injected" discipline this project's backend already
/// holds itself to (`core/db.py`'s pool is owned by `main.py`'s
/// lifespan, never created by a feature module for itself).
///
/// A second real correction, made when the real login screen
/// (`auth/auth_controller.dart`) landed: `accessToken` was originally a
/// fixed `String`, baked in once at fetcher-creation time. A real
/// access token is only valid for 15 minutes
/// (`ACCESS_TOKEN_TTL_MINUTES`) -- a fixed string would silently go
/// stale for any real session that outlives one fetch. `getAccessToken`
/// is now a real, injected async function, called fresh on every
/// single request; the real, live implementation
/// (`AuthController.getValidAccessToken()`) refreshes proactively
/// before the token actually expires.
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
