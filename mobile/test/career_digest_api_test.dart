// Real tests for api/career_digest_api.dart. Zero Flutter dependencies,
// mirrors gate_reveal_api_test.dart's own established parameterized-
// fetcher pattern -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/career_digest_api.dart';
import 'package:quorum_mobile/features/career_digest/career_digest_logic.dart';

void main() {
  group('createCareerDigestFetcher', () {
    test('sends the real Bearer header and the real application id in the URL path', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode({'company': 'Notion', 'summary_points': [], 'source_count': 0}), 200);
      });

      final fetch = createCareerDigestFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch('real-application-id');

      expect(capturedUri.toString(), 'https://example.test/career_pipeline/real-application-id/digest');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('URL-encodes the real application id in the path', () async {
      late Uri capturedUri;
      final client = MockClient((request) async {
        capturedUri = request.url;
        return http.Response(jsonEncode({'company': 'Notion', 'summary_points': [], 'source_count': 0}), 200);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client, baseUrl: 'https://example.test');
      await fetch('id with spaces/slash');

      expect(capturedUri.toString(), 'https://example.test/career_pipeline/id%20with%20spaces%2Fslash/digest');
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch('some-id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('parses a real, complete 200 response into CompanyDigestData', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'company': 'Notion',
            'summary_points': ['Raised a Series C round in 2021.', 'Growing fast.'],
            'source_count': 3,
          }),
          200,
        );
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);
      final digest = await fetch('real-id');

      expect(digest.company, 'Notion');
      expect(digest.summaryPoints, ['Raised a Series C round in 2021.', 'Growing fast.']);
      expect(digest.sourceCount, 3);
    });

    test('a real, genuine empty digest parses to a real, empty summaryPoints list, not a crash', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'company': 'Notion', 'summary_points': [], 'source_count': 0}), 200);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);
      final digest = await fetch('real-id');

      expect(digest.summaryPoints, isEmpty);
      expect(hasNoRealContent(digest), isTrue);
    });

    test('a real 404 throws the real, distinct DigestNotYetAvailableException, never a generic ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'No digest found for that application.'}), 404);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('missing-id');
        fail('should have thrown');
      } on DigestNotYetAvailableException catch (e) {
        expect(e.applicationId, 'missing-id');
      }
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch('real-id');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(e.statusCode, 401);
      }
    });

    test('a real 503 (dependency unavailable) throws a real, non-auth ApiException', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Database is not currently reachable'}), 503);
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('real-id');
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

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch('real-id');
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

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('real-id'), throwsA(isA<ApiException>()));
    });

    test('a real, well-formed body missing a required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'company': 'Notion', 'summary_points': []}), 200); // missing source_count
      });

      final fetch = createCareerDigestFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch('real-id'), throwsA(isA<ApiException>()));
    });
  });
}
