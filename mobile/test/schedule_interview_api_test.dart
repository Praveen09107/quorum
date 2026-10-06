// Real tests for api/schedule_interview_api.dart (`DEC-195`, product
// rebuild Block F remainder). Zero Flutter dependencies, mirrors
// create_application_api_test.dart's own established pattern exactly.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/schedule_interview_api.dart';

void main() {
  group('createScheduleInterviewFetcher', () {
    test('sends the real Bearer header, base URL, and a real JSON body', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'stakes': 'S1', 'decision': 'approve'}), 200);
      });

      final fetch = createScheduleInterviewFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch(applicationId: 'app_1', scheduledAt: DateTime.utc(2027, 3, 1, 10), format: 'video');

      expect(capturedUri.toString(), 'https://example.test/interviews');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody['application_id'], 'app_1');
      expect(capturedBody['scheduled_at_iso'], '2027-03-01T10:00:00.000Z');
      expect(capturedBody['format'], 'video');
    });

    test('a null scheduledAt/format serialize to real nulls, not a crash', () async {
      late Map<String, dynamic> capturedBody;
      final client = MockClient((request) async {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'stakes': 'S1', 'decision': 'approve'}), 200);
      });

      final fetch = createScheduleInterviewFetcher(getAccessToken: () async => 't', client: client);
      await fetch(applicationId: 'app_1');

      expect(capturedBody['scheduled_at_iso'], isNull);
      expect(capturedBody['format'], isNull);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createScheduleInterviewFetcher(getAccessToken: () async => null, client: client);

      await expectLater(
        fetch(applicationId: 'app_1'),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
      expect(requestSent, isFalse);
    });

    test('parses a real, complete 200 response', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'executed': false, 'stakes': 'S1', 'decision': 'approve'}), 200);
      });

      final fetch = createScheduleInterviewFetcher(getAccessToken: () async => 't', client: client);
      final result = await fetch(applicationId: 'app_1');

      expect(result.executed, isFalse);
      expect(result.decision, 'approve');
    });

    test('a real 502 surfaces the real backend-provided detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'A real, honest validation failure'}), 502);
      });

      final fetch = createScheduleInterviewFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(
        fetch(applicationId: 'app_1'),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'A real, honest validation failure')),
      );
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final fetch = createScheduleInterviewFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(applicationId: 'app_1'), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });
  });
}
