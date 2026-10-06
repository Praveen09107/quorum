// Real tests for api/week_summary_api.dart. Zero Flutter dependencies,
// mirrors today_api_test.dart's own established fetcher pattern --
// package:http's MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/week_summary_api.dart';

void main() {
  group('createWeekSummaryFetcher', () {
    test('sends the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'tasks_due_this_week': 2, 'month_to_date_spend': 100.0, 'monthly_budget_limit': 50000.0,
            'applications_in_progress': 3, 'waiting_on_count': 1,
          }),
          200,
        );
      });

      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/today/summary');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete 200 response into WeekSummaryData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'tasks_due_this_week': 2, 'month_to_date_spend': 150.5, 'monthly_budget_limit': 50000.0,
            'applications_in_progress': 3, 'waiting_on_count': 1,
          }),
          200,
        );
      });

      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.tasksDueThisWeek, 2);
      expect(data.monthToDateSpend, 150.5);
      expect(data.monthlyBudgetLimit, 50000.0);
      expect(data.applicationsInProgress, 3);
      expect(data.waitingOnCount, 1);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createWeekSummaryFetcher(getAccessToken: () async => null, client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'expired'}), 401));
      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
      }
    });

    test('a real 503 throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not available'}), 503));
      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a 200 with a missing required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'tasks_due_this_week': 1}), 200));
      final fetch = createWeekSummaryFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
