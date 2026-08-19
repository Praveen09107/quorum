// Real tests for api/trust_digest_api.dart -- the first real HTTP-calling
// code in this mobile codebase's history. Zero Flutter dependencies (the
// file under test only needs package:http), so plain `package:test`,
// `dart test` is the real verification -- same discipline as every other
// pure-logic file in this project.
//
// Uses package:http's own MockClient (no separate mock library needed)
// to test THIS file's own request-construction and response-parsing
// logic without needing real network access in the automated suite --
// the real, live backend was independently verified separately (see
// DECISIONS_LOG.md), the same "one real manual proof, then fast
// deterministic tests for everything else" pattern already used
// throughout this project's credential verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/trust_digest_api.dart';
import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';

void main() {
  group('createTrustDigestFetcher', () {
    test('sends the real Bearer header (fetched fresh via getAccessToken) and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'current_week': {'week_start': '2026-08-17', 'total_actions': 0, 'success_rate': 0.0},
            'previous_week': null,
            'trend': 'insufficient_data',
            'delta': null,
          }),
          200,
        );
      });

      final fetch = createTrustDigestFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/trust_digest');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('calls getAccessToken fresh on every real request, never caching a stale value', () async {
      var callCount = 0;
      final tokens = ['token-1', 'token-2'];
      final capturedAuthHeaders = <String?>[];

      final client = MockClient((request) async {
        capturedAuthHeaders.add(request.headers['Authorization']);
        return http.Response(
          jsonEncode({
            'current_week': {'week_start': '2026-08-17', 'total_actions': 0, 'success_rate': 0.0},
            'previous_week': null,
            'trend': 'insufficient_data',
            'delta': null,
          }),
          200,
        );
      });

      final fetch = createTrustDigestFetcher(
        getAccessToken: () async => tokens[callCount++],
        client: client,
      );
      await fetch();
      await fetch();

      expect(capturedAuthHeaders, ['Bearer token-1', 'Bearer token-2']);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into TrustDigestData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'current_week': {'week_start': '2026-08-10', 'total_actions': 24, 'success_rate': 0.875},
            'previous_week': {'week_start': '2026-08-03', 'total_actions': 19, 'success_rate': 0.789},
            'trend': 'improving',
            'delta': 0.086,
          }),
          200,
        );
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 't', client: client);
      final digest = await fetch();

      expect(digest.currentWeek.weekStart, '2026-08-10');
      expect(digest.currentWeek.totalActions, 24);
      expect(digest.currentWeek.successRate, 0.875);
      expect(digest.previousWeek, isNotNull);
      expect(digest.previousWeek!.totalActions, 19);
      expect(digest.trend, TrustTrend.improving);
      expect(digest.delta, 0.086);
    });

    test('a null previous_week parses to a real null, not a crash', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'current_week': {'week_start': '2026-08-17', 'total_actions': 0, 'success_rate': 0.0},
            'previous_week': null,
            'trend': 'insufficient_data',
            'delta': null,
          }),
          200,
        );
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 't', client: client);
      final digest = await fetch();

      expect(digest.previousWeek, isNull);
      expect(digest.trend, TrustTrend.insufficientData);
      expect(digest.delta, isNull);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 503 (database unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Database is not currently reachable'}), 503);
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isFalse);
        expect(e.statusCode, 503);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async {
        return http.Response('not json at all', 200);
      });

      final fetch = createTrustDigestFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
