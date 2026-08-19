// Real tests for api/account_api.dart. Zero Flutter dependencies,
// mirrors finance_api_test.dart's own established pattern exactly --
// package:http's MockClient, no separate mock library, `dart test` is
// the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/account_api.dart';
import 'package:quorum_mobile/api/api_exceptions.dart';

void main() {
  group('createAccountDeletionConfirmer', () {
    test('sends a real DELETE request with the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      late String capturedMethod;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        capturedMethod = request.method;
        return http.Response(
          jsonEncode({
            'user_id': 'u1',
            'sessions_revoked': true,
            'postgres_rows_deleted': 2,
            'vector_embeddings_deleted': 0,
            'memories_deleted': 0,
            'oauth_tokens_revoked': 0,
          }),
          200,
        );
      });

      final confirm = createAccountDeletionConfirmer(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await confirm();

      expect(capturedUri.toString(), 'https://example.test/account');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedMethod, 'DELETE');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => null, client: client);

      try {
        await confirm();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into DeletionResultData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'user_id': 'real-uuid-1234',
            'sessions_revoked': true,
            'postgres_rows_deleted': 12,
            'vector_embeddings_deleted': 340,
            'memories_deleted': 5,
            'oauth_tokens_revoked': 2,
          }),
          200,
        );
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 't', client: client);
      final result = await confirm();

      expect(result.sessionsRevoked, isTrue);
      expect(result.postgresRowsDeleted, 12);
      expect(result.vectorEmbeddingsDeleted, 340);
      expect(result.memoriesDeleted, 5);
      expect(result.oauthTokensRevoked, 2);
    });

    test('a real, honest result with two disclosed zero stores parses correctly', () async {
      // The real, current, disclosed shape: memories/oauth are always
      // zero in this backend (no mem0 integration, no persisted Google
      // tokens) -- proven parseable, not just a hypothetical shape.
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'user_id': 'real-uuid-5678',
            'sessions_revoked': true,
            'postgres_rows_deleted': 1,
            'vector_embeddings_deleted': 0,
            'memories_deleted': 0,
            'oauth_tokens_revoked': 0,
          }),
          200,
        );
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 't', client: client);
      final result = await confirm();

      expect(result.memoriesDeleted, 0);
      expect(result.oauthTokensRevoked, 0);
      expect(result.nonZeroStoreCounts.containsKey('memory'), isFalse);
      expect(result.nonZeroStoreCounts.containsKey('OAuth token'), isFalse);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 'expired', client: client);

      try {
        await confirm();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 503 (database unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Database is not currently reachable'}), 503);
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 't', client: client);

      try {
        await confirm();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isFalse);
        expect(e.statusCode, 503);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async {
        throw http.ClientException('Connection refused');
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 't', client: client);

      try {
        await confirm();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
        expect(e.isAuthFailure, isFalse);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async {
        return http.Response('not json at all', 200);
      });

      final confirm = createAccountDeletionConfirmer(getAccessToken: () async => 't', client: client);

      await expectLater(confirm(), throwsA(isA<ApiException>()));
    });
  });
}
