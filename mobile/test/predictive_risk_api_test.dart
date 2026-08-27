// Real tests for api/predictive_risk_api.dart. Zero Flutter
// dependencies, mirrors career_digest_api_test.dart's own established
// parameterized-fetcher pattern -- package:http's MockClient, no
// separate mock library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/predictive_risk_api.dart';

void main() {
  group('createPredictiveRiskFetcher', () {
    test('sends the real Bearer header and hits the real /predictive_risk path', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'week_start': '2026-09-01', 'deadline_density': 0, 'matching_historical_weeks': 0,
            'pooled_correction_rate': null, 'is_at_risk': false,
          }),
          200,
        );
      });

      final fetch = createPredictiveRiskFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/predictive_risk');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response with a real, non-null pooled_correction_rate', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'week_start': '2026-09-01', 'deadline_density': 3, 'matching_historical_weeks': 2,
            'pooled_correction_rate': 0.6, 'is_at_risk': true,
          }),
          200,
        );
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);
      final risk = await fetch();

      expect(risk.weekStart, DateTime.parse('2026-09-01'));
      expect(risk.deadlineDensity, 3);
      expect(risk.matchingHistoricalWeeks, 2);
      expect(risk.pooledCorrectionRate, 0.6);
      expect(risk.isAtRisk, isTrue);
    });

    test('a real, genuine no-data response parses pooled_correction_rate as a real null, never a fabricated 0.0', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'week_start': '2026-09-01', 'deadline_density': 0, 'matching_historical_weeks': 0,
            'pooled_correction_rate': null, 'is_at_risk': false,
          }),
          200,
        );
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);
      final risk = await fetch();

      expect(risk.pooledCorrectionRate, isNull);
      expect(risk.matchingHistoricalWeeks, 0);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 503 (dependency unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Database is not currently reachable'}), 503);
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a real, well-formed body missing a required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'week_start': '2026-09-01', 'deadline_density': 0}), 200);
      });

      final fetch = createPredictiveRiskFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
