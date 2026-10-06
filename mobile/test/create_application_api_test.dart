// Real tests for api/create_application_api.dart (`DEC-194`, product
// rebuild Block F). Zero Flutter dependencies, mirrors
// career_pipeline_api_test.dart's own established pattern exactly --
// package:http's MockClient, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/create_application_api.dart';

void main() {
  group('createCreateApplicationFetcher', () {
    test('sends the real Bearer header, base URL, and a real JSON body', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'company': 'Stripe'}), 200);
      });

      final fetch = createCreateApplicationFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch(company: 'Stripe', role: 'Backend Engineer');

      expect(capturedUri.toString(), 'https://example.test/applications');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody['company'], 'Stripe');
      expect(capturedBody['role'], 'Backend Engineer');
      expect(capturedBody['deadline_iso'], isNull);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createCreateApplicationFetcher(getAccessToken: () async => null, client: client);

      await expectLater(
        fetch(company: 'Stripe'),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
      expect(requestSent, isFalse);
    });

    test('parses a real, complete 200 response', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'executed': true, 'decision': 'approve', 'company': 'Stripe'}), 200);
      });

      final fetch = createCreateApplicationFetcher(getAccessToken: () async => 't', client: client);
      final result = await fetch(company: 'Stripe');

      expect(result.executed, isTrue);
      expect(result.decision, 'approve');
      expect(result.company, 'Stripe');
    });

    test('a real 502 surfaces the real backend-provided detail message', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'A real, honest validation failure'}), 502);
      });

      final fetch = createCreateApplicationFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(
        fetch(company: ''),
        throwsA(isA<ApiException>().having((e) => e.message, 'message', 'A real, honest validation failure')),
      );
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final fetch = createCreateApplicationFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(company: 'Stripe'), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', isNull)));
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw crash', () async {
      final client = MockClient((request) async {
        return http.Response('not json at all', 200);
      });

      final fetch = createCreateApplicationFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(company: 'Stripe'), throwsA(isA<ApiException>()));
    });
  });
}
