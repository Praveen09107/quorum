// Real tests for api/action_status_api.dart (`DEC-201`, product
// rebuild). Zero Flutter dependencies, mirrors week_summary_api_test
// .dart's own established fetcher pattern -- package:http's
// MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/action_status_api.dart';
import 'package:quorum_mobile/api/api_exceptions.dart';

void main() {
  group('createActionStatusFetcher', () {
    test('sends the real Bearer header and a real, path-parameterized URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'proposal_id': 'p1', 'action_type': 'create_task', 'stakes': 'S1', 'gate_decision': 'approve',
            'outcome': 'approved_unchanged', 'created_at': null, 'resolved_at': null, 'payload': {},
            'timeline': null, 'revision_count': null, 'pre_revision_payload': null, 'artifact': null,
          }),
          200,
        );
      });

      final fetch = createActionStatusFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await fetch('p1');

      expect(capturedUri.toString(), 'https://example.test/actions/p1/status');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete response including a real recorded timeline', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'proposal_id': 'p1', 'action_type': 'update_budget', 'stakes': 'S2', 'gate_decision': 'approve',
            'outcome': 'approved_unchanged', 'created_at': '2026-10-01T12:00:00+00:00', 'resolved_at': '2026-10-01T12:00:05+00:00',
            'payload': {'amount': 55000.0}, 'timeline': [{'event': 'routing', 'at_ms': 10}],
            'revision_count': 1, 'pre_revision_payload': {'amount': 60000.0}, 'artifact': null,
          }),
          200,
        );
      });

      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch('p1');

      expect(data.actionType, 'update_budget');
      expect(data.stakes, 'S2');
      expect(data.timeline, [{'event': 'routing', 'at_ms': 10}]);
      expect(data.revisionCount, 1);
      expect(data.preRevisionPayload, {'amount': 60000.0});
      expect(data.payload, {'amount': 55000.0});
    });

    test('a real, honest null timeline (pre-dating timeline recording) is never an empty list', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'proposal_id': 'p1', 'action_type': 'create_task', 'stakes': 'S1', 'gate_decision': 'approve',
            'outcome': 'approved_unchanged', 'created_at': null, 'resolved_at': null, 'payload': {},
            'timeline': null, 'revision_count': null, 'pre_revision_payload': null, 'artifact': null,
          }),
          200,
        );
      });

      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch('p1');

      expect(data.timeline, isNull);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createActionStatusFetcher(getAccessToken: () async => null, client: client);

      await expectLater(fetch('p1'), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
      expect(requestSent, isFalse);
    });

    test('a real 404 (no such action for this user) throws a real, distinct ApiException', () async {
      final client = MockClient((request) async => http.Response('', 404));
      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('p1'), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 404)));
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('p1'), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw crash', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('p1'), throwsA(isA<ApiException>()));
    });

    test('a 200 with a missing required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'proposal_id': 'p1'}), 200));
      final fetch = createActionStatusFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('p1'), throwsA(isA<ApiException>()));
    });
  });
}
