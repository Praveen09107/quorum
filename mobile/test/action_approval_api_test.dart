// Real tests for api/action_approval_api.dart. Zero Flutter
// dependencies, mirrors negotiation_api_test.dart's own established
// parameterized-fetcher pattern -- package:http's MockClient, no
// separate mock library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/action_approval_api.dart';
import 'package:quorum_mobile/api/api_exceptions.dart';

void main() {
  group('createApproveActionFetcher', () {
    test('sends the real Bearer header and the real proposal id in the URL path', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response('{}', 200);
      });

      final approve = createApproveActionFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await approve('real-proposal-id');

      expect(capturedUri.toString(), 'https://example.test/actions/real-proposal-id/approve');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('a null access token fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final approve = createApproveActionFetcher(getAccessToken: () async => null, client: client);

      await expectLater(approve('id'), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 200 completes without throwing', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'status': 'approved'}), 200));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);
      await approve('id'); // must not throw
    });

    test('a real 404 throws a distinct ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not found'}), 404));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await approve('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
      }
    });

    test('a real 409 surfaces the real, specific backend detail verbatim', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': "The Gate's own verdict on this action was 'reject'."}), 409));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await approve('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 409);
        expect(e.message, "The Gate's own verdict on this action was 'reject'.");
      }
    });

    test('a real 502 surfaces the real, specific execution-failure detail verbatim', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'Your Google account needs to be reconnected before this can be approved.'}), 502));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await approve('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 502);
        expect(e.message, 'Your Google account needs to be reconnected before this can be approved.');
      }
    });

    test('a real 503 throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not configured'}), 503));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await approve('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final approve = createApproveActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await approve('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });
  });

  group('createRejectActionFetcher', () {
    test('sends the real Bearer header and the real proposal id in the URL path', () async {
      late Uri capturedUri;
      final client = MockClient((request) async {
        capturedUri = request.url;
        return http.Response('{}', 200);
      });

      final reject = createRejectActionFetcher(getAccessToken: () async => 't', client: client, baseUrl: 'https://example.test');
      await reject('real-id');

      expect(capturedUri.toString(), 'https://example.test/actions/real-id/reject');
    });

    test('a real 200 completes without throwing', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'status': 'rejected'}), 200));
      final reject = createRejectActionFetcher(getAccessToken: () async => 't', client: client);
      await reject('id'); // must not throw
    });

    test('a real 409 surfaces the real, specific backend detail verbatim', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'This action has already been resolved.'}), 409));
      final reject = createRejectActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await reject('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 409);
        expect(e.message, 'This action has already been resolved.');
      }
    });

    test('a real 404 throws a distinct ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not found'}), 404));
      final reject = createRejectActionFetcher(getAccessToken: () async => 't', client: client);

      try {
        await reject('id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 404);
      }
    });
  });
}
