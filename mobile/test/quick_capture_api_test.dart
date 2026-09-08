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
          jsonEncode({'executed': true, 'decision': 'approve', 'stakes': 'S1', 'domain': 'tasks', 'title': 'A real task', 'findings': [], 'objections': []}),
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
            'domain': 'tasks',
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
            'domain': 'tasks',
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

    test('parses a real, genuine finance approve (Session 4) into QuickCaptureResultData with real amount/category/financeAction', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': true,
            'decision': 'approve',
            'stakes': 'S1',
            'domain': 'finance',
            'title': null,
            'amount': 800.0,
            'category': 'groceries',
            'finance_action': 'log_expense',
            'findings': [],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('spent 800 on groceries');

      expect(result.executed, isTrue);
      expect(result.domain, 'finance');
      expect(result.title, isNull);
      expect(result.amount, 800.0);
      expect(result.category, 'groceries');
      expect(result.financeAction, 'log_expense');
    });

    test('parses a real, genuine calendar review (Session 5) into QuickCaptureResultData with a real calendarAction, even though executed is false', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': false,
            'decision': 'approve',
            'stakes': 'S3',
            'domain': 'calendar',
            'title': null,
            'event_start': null,
            'event_end': null,
            'event_title': null,
            'calendar_action': 'create_calendar_event_external',
            'findings': [],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('set up a call with jane@company.com next Tuesday at 10');

      expect(result.executed, isFalse);
      expect(result.domain, 'calendar');
      expect(result.stakes, 'S3');
      // The real, load-bearing parsing proof: `calendar_action` is
      // genuinely readable even when `executed` is false -- the one
      // real field this domain deliberately populates regardless.
      expect(result.calendarAction, 'create_calendar_event_external');
    });

    test('parses a real, genuine career status update (Session 6) into QuickCaptureResultData with real company/newStatus/operation', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': true,
            'decision': 'approve',
            'stakes': 'S1',
            'domain': 'career',
            'operation': 'update',
            'title': null,
            'company': 'Notion',
            'new_status': 'rejected',
            'findings': [],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('mark the Notion application as rejected');

      expect(result.executed, isTrue);
      expect(result.domain, 'career');
      expect(result.operation, 'update');
      expect(result.company, 'Notion');
      expect(result.newStatus, 'rejected');
    });

    test('parses a real, genuine email review (Session 7) into QuickCaptureResultData with real emailAction, never executed', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'executed': false,
            'decision': 'approve',
            'stakes': 'S3',
            'domain': 'email',
            'operation': 'create',
            'title': null,
            'email_recipient': null,
            'email_action': 'send_email',
            'findings': [],
            'objections': [],
          }),
          200,
        );
      });

      final capture = createQuickCaptureFetcher(getAccessToken: () async => 'token', client: client);
      final result = await capture('tell Sarah the proposal looks good');

      expect(result.executed, isFalse);
      expect(result.domain, 'email');
      expect(result.stakes, 'S3');
      expect(result.emailAction, 'send_email');
      expect(result.emailRecipient, isNull); // never shown before a genuine send, which never happens through this real route today
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
