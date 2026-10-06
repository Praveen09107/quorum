// Real tests for api/gate_showcase_api.dart (`DEC-193`). Zero Flutter
// dependency -- package:http's MockClient, `dart test` is the real
// verification, matching agents_api_test.dart's own established
// pattern.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/gate_showcase_api.dart';

void main() {
  group('createGateValidatorsFetcher', () {
    test('throws a real 401 before ever sending a request when the token is null', () async {
      final fetch = createGateValidatorsFetcher(
        getAccessToken: () async => null,
        client: MockClient((request) async => fail('must not reach the network')),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
    });

    test('parses a real validator roster, including a not-wired validator', () async {
      final fetch = createGateValidatorsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async {
          expect(request.url.path, '/gate/validators');
          expect(request.headers['Authorization'], 'Bearer tok');
          return http.Response(
            jsonEncode({
              'validators': [
                {
                  'name': 'ProvenanceCheck', 'function_name': 'provenance_check',
                  'description': 'Checks the claimed source exists.', 'evidence_source': 'database lookup',
                  'wired': true,
                },
                {
                  'name': 'PIILeakCheck', 'function_name': 'pii_leak_check',
                  'description': 'Checks for leaked PII.', 'evidence_source': 'regex scan', 'wired': false,
                },
              ],
            }),
            200,
          );
        }),
      );

      final validators = await fetch();
      expect(validators.length, 2);
      expect(validators[0].wired, isTrue);
      expect(validators[1].wired, isFalse);
    });

    test('a non-200 response is a real, honest ApiException carrying the real status code', () async {
      final fetch = createGateValidatorsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async => http.Response('', 500)),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 500)));
    });
  });

  group('createGateStatsFetcher', () {
    test('throws a real 401 before ever sending a request when the token is null', () async {
      final fetch = createGateStatsFetcher(
        getAccessToken: () async => null,
        client: MockClient((request) async => fail('must not reach the network')),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
    });

    test('parses real stats including honest nulls for catch_rate and quota', () async {
      final fetch = createGateStatsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async {
          expect(request.url.path, '/gate/stats');
          return http.Response(
            jsonEncode({
              'total_resolved': 0, 'stakes_counts': <String, dynamic>{}, 'success_count': 0, 'caught_count': 0,
              'rejected_count': 0, 'uncertain_count': 0, 'catch_rate': null, 'rows_with_recorded_timeline': 0,
              'stage_b_ran_count': 0, 'revised_count': 0, 'quota_used': null, 'quota_limit': null,
            }),
            200,
          );
        }),
      );

      final stats = await fetch();
      expect(stats.totalResolved, 0);
      expect(stats.catchRate, isNull);
      expect(stats.quotaUsed, isNull);
    });

    test('a malformed real 200 body is a real, honest ApiException, never a raw crash', () async {
      final fetch = createGateStatsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async => http.Response('not json', 200)),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
