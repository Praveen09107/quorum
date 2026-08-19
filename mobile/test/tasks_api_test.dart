// Real tests for api/tasks_api.dart. Zero Flutter dependencies, mirrors
// trust_api_test.dart's own established pattern exactly -- package:http's
// MockClient, no separate mock library, `dart test` is the real
// verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/tasks_api.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';

void main() {
  group('createTasksFetcher', () {
    test('sends the real Bearer header (fetched fresh via getAccessToken) and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode([]), 200);
      });

      final fetch = createTasksFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/tasks');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('calls getAccessToken fresh on every real request, never caching a stale value', () async {
      var callCount = 0;
      final tokens = ['token-1', 'token-2'];
      final capturedAuthHeaders = <String?>[];

      final client = MockClient((request) async {
        capturedAuthHeaders.add(request.headers['Authorization']);
        return http.Response(jsonEncode([]), 200);
      });

      final fetch = createTasksFetcher(getAccessToken: () async => tokens[callCount++], client: client);
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

      final fetch = createTasksFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into a list of TaskData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {
              'task_id': 't1',
              'title': 'Finish the Q3 budget review',
              'estimated_hours': 2.5,
              'deadline': '2026-08-20T00:00:00Z',
              'status': 'open',
            },
          ]),
          200,
        );
      });

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);
      final tasks = await fetch();

      expect(tasks, hasLength(1));
      expect(tasks.first.taskId, 't1');
      expect(tasks.first.title, 'Finish the Q3 budget review');
      expect(tasks.first.estimatedHours, 2.5);
      expect(tasks.first.deadline, DateTime.parse('2026-08-20T00:00:00Z'));
      expect(tasks.first.status, TaskStatus.open);
    });

    test('a real null deadline parses to a real null, not a crash', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {
              'task_id': 't2',
              'title': 'A task with no deadline',
              'estimated_hours': 1.0,
              'deadline': null,
              'status': 'done',
            },
          ]),
          200,
        );
      });

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);
      final tasks = await fetch();

      expect(tasks.first.deadline, isNull);
      expect(tasks.first.status, TaskStatus.done);
    });

    test('an empty real list parses to a real empty list, not a crash', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode([]), 200);
      });

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);
      final tasks = await fetch();

      expect(tasks, isEmpty);
    });

    test('a genuinely unrecognized status fails loud, matching tasks.status\'s real closed-set contract', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {
              'task_id': 't3',
              'title': 'A task with a corrupted status',
              'estimated_hours': 1.0,
              'deadline': null,
              'status': 'not_a_real_status',
            },
          ]),
          200,
        );
      });

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ArgumentError>()));
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createTasksFetcher(getAccessToken: () async => 'expired', client: client);

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

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);

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

      final fetch = createTasksFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
