// Real tests for api/create_calendar_event_api.dart (`DEC-206`, product
// rebuild). Zero Flutter dependencies, mirrors
// update_budget_api_test.dart's own established pattern exactly --
// package:http's MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/create_calendar_event_api.dart';

void main() {
  group('createCreateCalendarEventFetcher', () {
    final start = DateTime.utc(2027, 3, 1, 10);
    final end = DateTime.utc(2027, 3, 1, 10, 30);

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
        return http.Response(jsonEncode({'executed': false, 'decision': 'approve', 'event_title': 'Sync', 'event_start': start.toIso8601String(), 'event_end': end.toIso8601String()}), 200);
      });

      final fetch = createCreateCalendarEventFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch(title: 'Sync', start: start, end: end);

      expect(capturedUri.toString(), 'https://example.test/calendar/events');
      expect(capturedMethod, 'POST');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody['title'], 'Sync');
      expect(capturedBody.containsKey('invitee_email'), isFalse);
    });

    test('includes invitee_email only when genuinely supplied', () async {
      late Map<String, dynamic> capturedBody;
      final client = MockClient((request) async {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': false, 'decision': 'escalate_to_human'}), 200);
      });

      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);
      await fetch(title: 'Sync', start: start, end: end, inviteeEmail: 'jane@company.com');

      expect(capturedBody['invitee_email'], 'jane@company.com');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => null, client: client);

      await expectLater(
        fetch(title: 'Sync', start: start, end: end),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
      expect(requestSent, isFalse);
    });

    test('parses a real, complete 200 response, including the real event fields the on-device write needs', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({'executed': false, 'decision': 'approve', 'event_title': 'Sync', 'event_start': start.toIso8601String(), 'event_end': end.toIso8601String()}),
          200,
        );
      });

      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);
      final result = await fetch(title: 'Sync', start: start, end: end);

      expect(result.decision, 'approve');
      expect(result.eventTitle, 'Sync');
      expect(result.eventStart, start);
      expect(result.eventEnd, end);
    });

    test('a real 502 surfaces the real backend-provided detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'A real, honest validation failure'}), 502);
      });

      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(
        fetch(title: '', start: start, end: end),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'A real, honest validation failure')),
      );
    });

    test('a real 503 (the Gate\'s reviewer unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch(title: 'Sync', start: start, end: end);
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(title: 'Sync', start: start, end: end), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw crash', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createCreateCalendarEventFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(title: 'Sync', start: start, end: end), throwsA(isA<ApiException>()));
    });
  });
}
