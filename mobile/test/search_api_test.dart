// Real tests for api/search_api.dart. Zero Flutter dependencies, mirrors
// today_api_test.dart/career_pipeline_api_test.dart's own established
// pattern exactly -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/search_api.dart';
import 'package:quorum_mobile/features/search/search_logic.dart';

List<Map<String, dynamic>> _realResponseBody() => [
      {
        'item_id': 'a-real-task-id',
        'item_type': 'task',
        'text': 'Finish Q3 budget review',
        'timestamp': '2026-08-10T09:00:00Z',
      },
      {
        'item_id': 'a-real-application-id',
        'item_type': 'application',
        // Deliberately carries the same real non-ASCII em-dash
        // `features/search.py`'s own `_content_for_application()`
        // genuinely emits -- see `_realJsonHeaders` below for why that
        // matters, and `utf8_decoding_proof_test.dart` for the full
        // real account.
        'text': 'Notion — Software Engineer',
        'timestamp': '2026-08-05T14:00:00Z',
      },
    ];

/// Exactly what this project's real FastAPI backend sends, confirmed
/// live via a real curl against the real Cloud Run URL: `application/
/// json`, no charset parameter. Load-bearing in these tests, not
/// decoration -- `http.Response(String, ...)` with no headers gets
/// `application/octet-stream` and therefore latin1, which genuinely
/// cannot encode the real non-ASCII content above.
const _realJsonHeaders = {'content-type': 'application/json'};

void main() {
  group('createSearchFetcher', () {
    test('sends a real GET request with the real query param, Bearer header, and base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode(_realResponseBody()), 200, headers: _realJsonHeaders);
      });

      final fetch = createSearchFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch('budget deadline');

      expect(capturedUri.path, '/search');
      expect(capturedUri.queryParameters['q'], 'budget deadline');
      expect(capturedUri.origin, 'https://example.test');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete 200 response -- every field, including the newer application type', () async {
      final client = MockClient((request) async => http.Response(jsonEncode(_realResponseBody()), 200, headers: _realJsonHeaders));
      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      final results = await fetch('anything');

      expect(results, hasLength(2));
      expect(results[0].itemId, 'a-real-task-id');
      expect(results[0].itemType, SearchItemType.task);
      expect(results[0].text, 'Finish Q3 budget review');
      expect(results[0].timestamp, DateTime.parse('2026-08-10T09:00:00Z'));

      expect(results[1].itemId, 'a-real-application-id');
      expect(results[1].itemType, SearchItemType.application);
      expect(results[1].text, 'Notion — Software Engineer');
    });

    test('a real, honest empty result parses correctly -- no matches for this query', () async {
      final client = MockClient((request) async => http.Response(jsonEncode(<Map<String, dynamic>>[]), 200));
      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      final results = await fetch('nothing matches this');

      expect(results, isEmpty);
    });

    test('an unrecognized item_type falls back to SearchItemType.unknown, never crashes', () async {
      final body = [
        {
          'item_id': 'x',
          'item_type': 'something_unrecognized',
          'text': 'irrelevant',
          'timestamp': '2026-08-10T09:00:00Z',
        },
      ];
      final client = MockClient((request) async => http.Response(jsonEncode(body), 200));
      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      final results = await fetch('anything');

      expect(results.single.itemType, SearchItemType.unknown);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createSearchFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createSearchFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 503 (embedding provider not configured) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': "Search is not currently available"}), 503);
      });

      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('anything');
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

      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('anything');
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

      final fetch = createSearchFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('anything'), throwsA(isA<ApiException>()));
    });
  });
}
