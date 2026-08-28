// Real tests for api/quick_capture_api.dart (`DEC-153`). Zero Flutter
// dependencies -- `dart test` is the real command, matching
// `trust_digest_api_test.dart`'s own established convention exactly
// (`package:http`'s own `MockClient`, no separate mock library).

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/quick_capture_api.dart';

void main() {
  group('createQuickCaptureFetcher', () {
    test('sends the real Bearer header, the real base URL, and the real JSON body', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({'executed': true, 'decision': 'approve', 'stakes': 'S1', 'title': 'A real task', 'findings': [], 'objections': []}),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await capture('finish the report');

      expect(capturedUri.toString(), 'https://example.test/quick_capture');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody, {'text': 'finish the report'});
    });

    test('a null access token fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => null, client: client);

      try {
        await capture('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, genuine approve into QuickCaptureResultData with real findings', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': true,
            'decision': 'approve',
            'stakes': 'S1',
            'title': 'A real, distinctive created task',
            'findings': [
              {'validator': 'provenance_check', 'claim': 'A real user request', 'evidence_state': 'verified_true'},
            ],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('finish the report');

      expect(result.executed, isTrue);
      expect(result.decision, 'approve');
      expect(result.title, 'A real, distinctive created task');
      expect(result.findings, hasLength(1));
      expect(result.findings.first.validator, 'provenance_check');
    });

    test('a real, genuine Stage A refusal parses to executed=false with a real title of null', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': false,
            'decision': 'revise',
            'stakes': 'S1',
            'title': null,
            'findings': [
              {'validator': 'deadline_conflict_check', 'claim': 'Not enough real capacity', 'evidence_state': 'verified_false'},
            ],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('an impossible task');

      expect(result.executed, isFalse);
      expect(result.title, isNull);
    });

    test('a real 502 (genuine extraction failure) surfaces the real backend detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': "Couldn't turn that into a real task: real reason"}), 502);
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await capture('gibberish');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 502);
        expect(e.message, contains('real reason'));
      }
    });

    test('a real 503 (extraction provider not configured) throws a real, distinct ApiException', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await capture('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
      }
    });

    test('a real 422 (blank text) throws a real, distinct ApiException', () async {
      final client = MockClient((request) async => http.Response('', 422));
      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await capture('   ');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 422);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw Exception('no real connectivity'));
      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await capture('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async => http.Response('not real json', 200));
      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await capture('anything');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });
  });
}
