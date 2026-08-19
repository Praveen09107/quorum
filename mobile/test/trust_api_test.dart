// Real tests for api/trust_api.dart. Zero Flutter dependencies, mirrors
// trust_digest_api_test.dart's own established pattern exactly --
// package:http's MockClient, no separate mock library, `dart test` is
// the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/trust_api.dart';
import 'package:quorum_mobile/features/trust/trust_logic.dart';

Map<String, dynamic> _realGateBody({
  int total = 3,
  int caught = 3,
  List<Map<String, dynamic>> missed = const [],
  List<Map<String, dynamic>>? results,
  String target = 'real_gate',
}) {
  return {
    'total': total,
    'caught': caught,
    'missed': missed,
    'results': results ??
        [
          {'scenario_id': 'S0_clean_approval', 'expected': 'approve', 'actual': 'approve', 'passed': true},
          {'scenario_id': 'S2_stage_a_hard_fail', 'expected': 'revise', 'actual': 'revise', 'passed': true},
          {
            'scenario_id': 'S3_real_critic_objection_escalates',
            'expected': 'escalate_to_human',
            'actual': 'escalate_to_human',
            'passed': true,
          },
        ],
    'target': target,
  };
}

void main() {
  group('createTrustFetcher', () {
    test('sends the real Bearer header (fetched fresh via getAccessToken) and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode(_realGateBody()), 200);
      });

      final fetch = createTrustFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/trust');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('calls getAccessToken fresh on every real request, never caching a stale value', () async {
      var callCount = 0;
      final tokens = ['token-1', 'token-2'];
      final capturedAuthHeaders = <String?>[];

      final client = MockClient((request) async {
        capturedAuthHeaders.add(request.headers['Authorization']);
        return http.Response(jsonEncode(_realGateBody()), 200);
      });

      final fetch = createTrustFetcher(getAccessToken: () async => tokens[callCount++], client: client);
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

      final fetch = createTrustFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into TrustData, including a real target of real_gate', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode(_realGateBody()), 200);
      });

      final fetch = createTrustFetcher(getAccessToken: () async => 't', client: client);
      final trust = await fetch();

      expect(trust.total, 3);
      expect(trust.caught, 3);
      expect(trust.missed, isEmpty);
      expect(trust.results, hasLength(3));
      expect(trust.target, SelfTestTarget.realGate);
      expect(trust.results.first.scenarioId, 'S0_clean_approval');
      expect(trust.results.first.passed, isTrue);
    });

    test('a real, non-empty missed list parses correctly and stays a genuine subset', () async {
      final missedScenario = {
        'scenario_id': 'deliberately_mis_specified',
        'expected': 'reject',
        'actual': 'approve',
        'passed': false,
      };
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode(_realGateBody(total: 1, caught: 0, missed: [missedScenario], results: [missedScenario])),
          200,
        );
      });

      final fetch = createTrustFetcher(getAccessToken: () async => 't', client: client);
      final trust = await fetch();

      expect(trust.missed, hasLength(1));
      expect(trust.missed.first.scenarioId, 'deliberately_mis_specified');
      expect(trust.missed.first.passed, isFalse);
    });

    test('an unrecognized target string parses to the honest, fail-closed stub value', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode(_realGateBody(target: 'something_unexpected')), 200);
      });

      final fetch = createTrustFetcher(getAccessToken: () async => 't', client: client);
      final trust = await fetch();

      expect(trust.target, SelfTestTarget.stub);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createTrustFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final fetch = createTrustFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createTrustFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
