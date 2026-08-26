// Real tests for api/honesty_log_api.dart. Zero Flutter dependencies,
// mirrors waiting_on_api_test.dart's own established pattern exactly --
// package:http's MockClient, no separate mock library, `dart test` is
// the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/honesty_log_api.dart';

void main() {
  group('createHonestyLogFetcher', () {
    test('sends the real Bearer header (fetched fresh via getAccessToken) and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'total': 0,
            'success_rate': null,
            'successes': [],
            'failures_and_catches': [],
            'genuinely_uncertain': [],
          }),
          200,
        );
      });

      final fetch = createHonestyLogFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/honesty_log');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createHonestyLogFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response with all three buckets and a real success rate', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'total': 2,
            'success_rate': 0.5,
            'successes': [
              {
                'action_id': 'a1',
                'timestamp': '2026-08-10T09:00:00Z',
                'outcome': 'approved_unchanged',
                'description': 'Created task: Write report',
              },
            ],
            'failures_and_catches': [
              {
                'action_id': 'a2',
                'timestamp': '2026-08-11T14:00:00Z',
                'outcome': 'caught_by_gate',
                'description': 'Draft claimed a meeting that didn\'t exist',
              },
            ],
            'genuinely_uncertain': [],
          }),
          200,
        );
      });

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);
      final feed = await fetch();

      expect(feed.total, 2);
      expect(feed.successRate, 0.5);
      expect(feed.successes, hasLength(1));
      expect(feed.successes.first.actionId, 'a1');
      expect(feed.successes.first.description, 'Created task: Write report');
      expect(feed.failuresAndCatches, hasLength(1));
      expect(feed.failuresAndCatches.first.outcome, 'caught_by_gate');
      expect(feed.genuinelyUncertain, isEmpty);
    });

    test('a real null success_rate parses to a real null, not zero -- "No data yet" is honest', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'total': 0,
            'success_rate': null,
            'successes': [],
            'failures_and_catches': [],
            'genuinely_uncertain': [
              {
                'action_id': 'a3',
                'timestamp': '2026-08-12T00:00:00Z',
                'outcome': 'uncertain_no_data',
                'description': 'Sent an email to a@x.com',
              },
            ],
          }),
          200,
        );
      });

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);
      final feed = await fetch();

      expect(feed.successRate, isNull);
      expect(feed.total, 0);
      expect(feed.genuinelyUncertain, hasLength(1));
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 'expired', client: client);

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

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a real, well-formed body missing a required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({'total': 0, 'success_rate': null, 'successes': []}), // missing failures_and_catches/genuinely_uncertain
          200,
        );
      });

      final fetch = createHonestyLogFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
