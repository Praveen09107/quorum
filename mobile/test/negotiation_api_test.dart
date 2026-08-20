// Real tests for api/negotiation_api.dart. Zero Flutter dependencies,
// mirrors today_api_test.dart/search_api_test.dart's own established
// pattern exactly -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/negotiation_api.dart';

const _realJsonHeaders = {'content-type': 'application/json'};

Map<String, dynamic> _realResponseBody() => {
      'positions': [
        {'domain': 'finance', 'concern': 'budget at risk', 'proposed_resolution': 'halt spending'},
      ],
      'options': [
        {
          'option_id': 'option_a',
          'description': 'halt spending',
          'source_domains': ['finance'],
          'impact': [
            {'metric': 'budget_remaining_fraction', 'before': 0.08, 'after': 0.18, 'direction': 'improves'},
          ],
        },
        {'option_id': 'do_nothing', 'description': 'do nothing', 'source_domains': <String>[], 'impact': <Map<String, dynamic>>[]},
      ],
    };

void main() {
  group('createNegotiationFetcher', () {
    test('sends a real GET request to the real negotiation-scoped URL with the real Bearer header', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode(_realResponseBody()), 200, headers: _realJsonHeaders);
      });

      final fetch = createNegotiationFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch('a-real-negotiation-id');

      expect(capturedUri.toString(), 'https://example.test/negotiations/a-real-negotiation-id');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete 200 response -- positions, options, and each option\'s impact', () async {
      final client = MockClient((request) async => http.Response(jsonEncode(_realResponseBody()), 200, headers: _realJsonHeaders));
      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

      final result = await fetch('a-real-negotiation-id');

      expect(result.positions, hasLength(1));
      expect(result.positions.first.domain, 'finance');
      expect(result.positions.first.concern, 'budget at risk');
      expect(result.positions.first.proposedResolution, 'halt spending');

      expect(result.options, hasLength(2));
      final optionA = result.options.firstWhere((o) => o.optionId == 'option_a');
      expect(optionA.sourceDomains, ['finance']);
      expect(optionA.impact, hasLength(1));
      expect(optionA.impact.first.metric, 'budget_remaining_fraction');
      expect(optionA.impact.first.direction, 'improves');

      final doNothing = result.options.firstWhere((o) => o.optionId == 'do_nothing');
      expect(doNothing.impact, isEmpty);
    });

    test('a real, honest in-progress negotiation (empty positions/options) parses correctly', () async {
      final body = {'positions': <Map<String, dynamic>>[], 'options': <Map<String, dynamic>>[]};
      final client = MockClient((request) async => http.Response(jsonEncode(body), 200, headers: _realJsonHeaders));
      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

      final result = await fetch('a-real-negotiation-id');

      expect(result.positions, isEmpty);
      expect(result.options, isEmpty);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createNegotiationFetcher(getAccessToken: () async => null, client: client);

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

      final fetch = createNegotiationFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 404 (no such negotiation, or not this caller\'s) throws a real, distinct ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'No negotiation found with that id.'}), 404);
      });

      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isFalse);
        expect(e.statusCode, 404);
      }
    });

    test('a real 503 throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Database is not currently reachable'}), 503);
      });

      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createNegotiationFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('anything'), throwsA(isA<ApiException>()));
    });
  });
}
