// Real tests for api/gate_reveal_api.dart. Zero Flutter dependencies,
// mirrors negotiation_api_test.dart's own established parameterized-
// fetcher pattern -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/gate_reveal_api.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';

void main() {
  group('createGateRevealFetcher', () {
    test('sends the real Bearer header and the real proposal id in the URL path', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode({'findings': [], 'objections': []}), 200);
      });

      final fetch = createGateRevealFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch('real-proposal-id');

      expect(capturedUri.toString(), 'https://example.test/gate_reveal/real-proposal-id');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch('some-id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into findings and objections with the real visual-state mapping', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'findings': [
              {'validator': 'ProvenanceCheck', 'claim': 'A real claim', 'evidence_state': 'verified_true'},
              {'validator': 'TemporalFactCheck', 'claim': 'Another claim', 'evidence_state': 'no_data_found'},
            ],
            'objections': [
              {'category': 'tone', 'severity': 'low', 'description': 'Fine.', 'signed_off': true},
            ],
          }),
          200,
        );
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);
      final bundle = await fetch('real-id');

      expect(bundle.findings, hasLength(2));
      expect(bundle.findings[0].validator, 'ProvenanceCheck');
      expect(bundle.findings[0].visualState, EvidenceVisualState.positive);
      expect(bundle.findings[1].visualState, EvidenceVisualState.uncertain);
      expect(bundle.objections, hasLength(1));
      expect(bundle.objections[0].signedOff, isTrue);
    });

    test('an empty real bundle parses to real empty lists, not a crash', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'findings': [], 'objections': []}), 200);
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);
      final bundle = await fetch('real-id');

      expect(bundle.findings, isEmpty);
      expect(bundle.objections, isEmpty);
    });

    test('a real 404 throws a real, distinct ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'No action found with that id.'}), 404);
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('missing-id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch('real-id');
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

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('real-id');
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

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('real-id');
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

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('real-id'), throwsA(isA<ApiException>()));
    });

    test('a real, well-formed item missing a required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'findings': [
              {'validator': 'ProvenanceCheck', 'claim': 'A real claim'}, // missing evidence_state
            ],
            'objections': [],
          }),
          200,
        );
      });

      final fetch = createGateRevealFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('real-id'), throwsA(isA<ApiException>()));
    });
  });
}
