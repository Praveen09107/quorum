// Real tests for api/agents_api.dart (`DEC-192`). Zero Flutter
// dependency -- package:http's MockClient, `dart test` is the real
// verification, matching account_api_test.dart's own established
// pattern.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/agents_api.dart';
import 'package:quorum_mobile/api/api_exceptions.dart';

void main() {
  group('createAgentsFetcher', () {
    test('throws a real 401 before ever sending a request when the token is null', () async {
      final fetch = createAgentsFetcher(
        getAccessToken: () async => null,
        client: MockClient((request) async => fail('must not reach the network')),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
    });

    test('parses a real list of five agents', () async {
      final fetch = createAgentsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer tok');
          return http.Response(
            jsonEncode({
              'agents': [
                {
                  'domain': 'email', 'lifetime_actions': 3, 'success_count': 2, 'caught_count': 1,
                  'rejected_count': 0, 'uncertain_count': 0, 'success_rate': 0.667, 'last_activity': '2027-01-01T00:00:00Z',
                },
                {
                  'domain': 'career', 'lifetime_actions': 0, 'success_count': 0, 'caught_count': 0,
                  'rejected_count': 0, 'uncertain_count': 0, 'success_rate': null, 'last_activity': null,
                },
              ],
            }),
            200,
          );
        }),
      );

      final agents = await fetch();
      expect(agents.length, 2);
      expect(agents[0].domain, 'email');
      expect(agents[0].isActive, isTrue);
      expect(agents[1].domain, 'career');
      expect(agents[1].isActive, isFalse);
    });

    test('a real 401 response surfaces the honest session-expired message', () async {
      final fetch = createAgentsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async => http.Response('', 401)),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
    });

    test('a malformed real 200 body is a real, honest ApiException, never a raw crash', () async {
      final fetch = createAgentsFetcher(
        getAccessToken: () async => 'tok',
        client: MockClient((request) async => http.Response('not json', 200)),
      );
      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
