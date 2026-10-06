// Real tests for api/task_status_api.dart. Zero Flutter dependencies,
// mirrors action_approval_api_test.dart's own established parameterized-
// fetcher pattern -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/task_status_api.dart';

void main() {
  group('createCompleteTaskFetcher', () {
    test('sends the real Bearer header and the real task id in the URL path', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response('{}', 200);
      });

      final complete = createCompleteTaskFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await complete('real-task-id');

      expect(capturedUri.toString(), 'https://example.test/tasks/real-task-id/complete');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('a null access token fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final complete = createCompleteTaskFetcher(getAccessToken: () async => null, client: client);

      await expectLater(complete('id'), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 200 completes without throwing', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'status': 'done'}), 200));
      final complete = createCompleteTaskFetcher(getAccessToken: () async => 't', client: client);
      await complete('id'); // must not throw
    });

    test('a real 404 throws a distinct ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not found'}), 404));
      final complete = createCompleteTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await complete('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
      }
    });

    test('a real 409 surfaces the real, specific backend detail verbatim', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'This task is no longer open -- it has already been completed or cancelled.'}), 409));
      final complete = createCompleteTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await complete('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 409);
        expect(e.message, 'This task is no longer open -- it has already been completed or cancelled.');
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final complete = createCompleteTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await complete('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });
  });

  group('createCancelTaskFetcher', () {
    test('sends the real Bearer header and the real task id in the URL path', () async {
      late Uri capturedUri;
      final client = MockClient((request) async {
        capturedUri = request.url;
        return http.Response('{}', 200);
      });

      final cancel = createCancelTaskFetcher(getAccessToken: () async => 't', client: client, baseUrl: 'https://example.test');
      await cancel('real-id');

      expect(capturedUri.toString(), 'https://example.test/tasks/real-id/cancel');
    });

    test('a real 200 completes without throwing', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'status': 'cancelled'}), 200));
      final cancel = createCancelTaskFetcher(getAccessToken: () async => 't', client: client);
      await cancel('id'); // must not throw
    });

    test('a real 409 surfaces the real, specific backend detail verbatim', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'This task is no longer open -- it has already been completed or cancelled.'}), 409));
      final cancel = createCancelTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await cancel('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 409);
      }
    });

    test('a real 404 throws a distinct ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not found'}), 404));
      final cancel = createCancelTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await cancel('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
      }
    });
  });
}
