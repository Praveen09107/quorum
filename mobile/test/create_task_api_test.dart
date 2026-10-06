// Real tests for api/create_task_api.dart (`DEC-208`, product
// rebuild). Zero Flutter dependencies, mirrors
// create_calendar_event_api_test.dart's own established pattern
// exactly -- package:http's MockClient, `dart test` is the real
// verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/create_task_api.dart';

void main() {
  group('createCreateTaskFetcher', () {
    test('sends a real POST with the Bearer header, base URL, and a real JSON body', () async {
      late Uri capturedUri;
      late String capturedMethod;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedMethod = request.method;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'title': 'Write the report'}), 200);
      });

      final fetch = createCreateTaskFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch(title: 'Write the report', estimatedHours: 2.0);

      expect(capturedUri.toString(), 'https://example.test/tasks');
      expect(capturedMethod, 'POST');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody['title'], 'Write the report');
      expect(capturedBody['estimated_hours'], 2.0);
      expect(capturedBody.containsKey('deadline_iso'), isFalse);
    });

    test('includes deadline_iso only when genuinely supplied', () async {
      late Map<String, dynamic> capturedBody;
      final client = MockClient((request) async {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve'}), 200);
      });

      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);
      await fetch(title: 'Write the report', estimatedHours: 2.0, deadline: DateTime.utc(2027, 3, 1));

      expect(capturedBody['deadline_iso'], '2027-03-01T00:00:00.000Z');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createCreateTaskFetcher(getAccessToken: () async => null, client: client);

      await expectLater(
        fetch(title: 'Write the report', estimatedHours: 2.0),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
      expect(requestSent, isFalse);
    });

    test('parses a real, complete 200 response', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'title': 'Write the report'}), 200);
      });

      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);
      final result = await fetch(title: 'Write the report', estimatedHours: 2.0);

      expect(result.executed, isTrue);
      expect(result.decision, 'approve');
      expect(result.title, 'Write the report');
    });

    test('a real 502 surfaces the real backend-provided detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'A real, honest validation failure'}), 502);
      });

      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(
        fetch(title: '', estimatedHours: 2.0),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'A real, honest validation failure')),
      );
    });

    test('a real 503 (the Gate\'s reviewer unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch(title: 'Write the report', estimatedHours: 2.0);
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(title: 'Write the report', estimatedHours: 2.0), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw crash', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createCreateTaskFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(title: 'Write the report', estimatedHours: 2.0), throwsA(isA<ApiException>()));
    });
  });
}
