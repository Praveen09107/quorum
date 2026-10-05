// Real tests for api/expenses_api.dart. Zero Flutter dependencies,
// mirrors tasks_api_test.dart's own established fetcher pattern --
// package:http's MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/expenses_api.dart';

void main() {
  group('createExpensesFetcher', () {
    test('sends the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response('[]', 200);
      });

      final fetch = createExpensesFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/finance/expenses');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete 200 response into a list of ExpenseData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {'expense_id': 'e1', 'payee': 'A real payee', 'amount': 42.5, 'occurred_at': '2026-09-28T10:00:00Z'},
          ]),
          200,
        );
      });

      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);
      final expenses = await fetch();

      expect(expenses, hasLength(1));
      expect(expenses[0].expenseId, 'e1');
      expect(expenses[0].payee, 'A real payee');
      expect(expenses[0].amount, 42.5);
      expect(expenses[0].occurredAt, DateTime.parse('2026-09-28T10:00:00Z'));
    });

    test('an empty real list parses to a real empty list, not a crash', () async {
      final client = MockClient((request) async => http.Response('[]', 200));
      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);
      expect(await fetch(), isEmpty);
    });

    test('a null access token fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createExpensesFetcher(getAccessToken: () async => null, client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'expired'}), 401));
      final fetch = createExpensesFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
      }
    });

    test('a real 503 throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not available'}), 503));
      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);

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
      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a real, well-formed item missing a required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {'expense_id': 'e1', 'payee': 'A real payee'}, // missing amount/occurred_at
          ]),
          200,
        );
      });

      final fetch = createExpensesFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
