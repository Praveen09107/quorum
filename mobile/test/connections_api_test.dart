// Real tests for api/connections_api.dart. Zero Flutter dependencies,
// mirrors week_summary_api_test.dart's own established fetcher
// pattern -- package:http's MockClient, `dart test` is the real
// verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/connections_api.dart';

void main() {
  group('createConnectionsFetcher', () {
    test('sends the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(
          jsonEncode({'connected': false, 'granted_scopes': [], 'last_updated_at': null, 'token_refreshable': null}),
          200,
        );
      });

      final fetch = createConnectionsFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/connections');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, honest not-connected response', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({'connected': false, 'granted_scopes': [], 'last_updated_at': null, 'token_refreshable': null}),
          200,
        );
      });

      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.connected, isFalse);
      expect(data.grantedScopes, isEmpty);
      expect(data.lastUpdatedAt, isNull);
      expect(data.tokenRefreshable, isNull);
    });

    test('parses a real, connected-and-healthy response with real granted scopes', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'connected': true,
            'granted_scopes': ['openid', 'email', 'https://www.googleapis.com/auth/gmail.readonly'],
            'last_updated_at': '2026-10-01T12:00:00+00:00',
            'token_refreshable': true,
          }),
          200,
        );
      });

      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.connected, isTrue);
      expect(data.grantedScopes, ['openid', 'email', 'https://www.googleapis.com/auth/gmail.readonly']);
      expect(data.lastUpdatedAt, DateTime.parse('2026-10-01T12:00:00+00:00'));
      expect(data.tokenRefreshable, isTrue);
    });

    test('parses a real, connected-but-not-refreshable response', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'connected': true,
            'granted_scopes': ['openid'],
            'last_updated_at': '2026-09-01T12:00:00+00:00',
            'token_refreshable': false,
          }),
          200,
        );
      });

      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.connected, isTrue);
      expect(data.tokenRefreshable, isFalse);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createConnectionsFetcher(getAccessToken: () async => null, client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'expired'}), 401));
      final fetch = createConnectionsFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
      }
    });

    test('a real 503 (Google OAuth not configured on this deployment) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'not configured'}), 503));
      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);

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
      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a 200 with a missing required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'connected': true}), 200));
      final fetch = createConnectionsFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
