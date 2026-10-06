// Real tests for api/update_budget_api.dart (`DEC-200`, product
// rebuild). Zero Flutter dependencies, mirrors
// create_application_api_test.dart's own established pattern exactly
// -- package:http's MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/update_budget_api.dart';

void main() {
  group('createUpdateBudgetFetcher', () {
    test('sends a real PUT with the Bearer header, base URL, and a real JSON body', () async {
      late Uri capturedUri;
      late String capturedMethod;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedMethod = request.method;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'amount': 60000.0}), 200);
      });

      final fetch = createUpdateBudgetFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch(amount: 60000.0, category: 'Groceries');

      expect(capturedUri.toString(), 'https://example.test/finance/budget');
      expect(capturedMethod, 'PUT');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody['amount'], 60000.0);
      expect(capturedBody['category'], 'Groceries');
    });

    test('omits category entirely from the real body when none is supplied', () async {
      late Map<String, dynamic> capturedBody;
      final client = MockClient((request) async {
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'amount': 60000.0}), 200);
      });

      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);
      await fetch(amount: 60000.0);

      expect(capturedBody.containsKey('category'), isFalse);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => null, client: client);

      await expectLater(
        fetch(amount: 1000),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
      expect(requestSent, isFalse);
    });

    test('parses a real, complete 200 response, including the real, possibly-revised amount', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'executed': true, 'decision': 'revise', 'amount': 55000.0}), 200);
      });

      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);
      final result = await fetch(amount: 60000.0);

      expect(result.executed, isTrue);
      expect(result.decision, 'revise');
      expect(result.amount, 55000.0);
    });

    test('a real 502 surfaces the real backend-provided detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'A real, honest validation failure'}), 502);
      });

      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(
        fetch(amount: -1),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'A real, honest validation failure')),
      );
    });

    test('a real 503 (the Gate\'s reviewer unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch(amount: 1000);
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(amount: 1000), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw crash', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createUpdateBudgetFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(amount: 1000), throwsA(isA<ApiException>()));
    });
  });
}
