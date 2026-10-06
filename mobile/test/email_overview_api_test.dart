// Real tests for api/email_overview_api.dart. Zero Flutter
// dependencies, mirrors week_summary_api_test.dart's own established
// fetcher pattern -- package:http's MockClient, `dart test` is the
// real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/email_overview_api.dart';

void main() {
  group('createEmailOverviewFetcher', () {
    test('sends the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode({'drafts': [], 'sent_history': [], 'known_recipients': []}), 200);
      });

      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 'a-real-test-token', client: client, baseUrl: 'https://example.test');
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/email/overview');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, honestly empty response', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'drafts': [], 'sent_history': [], 'known_recipients': []}), 200);
      });

      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.drafts, isEmpty);
      expect(data.sentHistory, isEmpty);
      expect(data.knownRecipients, isEmpty);
    });

    test('parses a real, complete response with a draft, a sent message, and a known recipient', () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'drafts': [
              {'proposal_id': 'p1', 'created_at': '2026-10-01T12:00:00+00:00', 'recipient': 'sarah@example.com', 'subject': 'Re: proposal', 'draft_id': 'draft-abc'},
            ],
            'sent_history': [
              {'recipient': 'bob@example.com', 'subject': 'a real subject', 'sent_at': '2026-09-30T12:00:00+00:00', 'replied_at': null},
            ],
            'known_recipients': [
              {'recipient': 'bob@example.com', 'last_contacted_at': '2026-09-30T12:00:00+00:00', 'message_count': 1},
            ],
          }),
          200,
        );
      });

      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 't', client: client);
      final data = await fetch();

      expect(data.drafts.single.recipient, 'sarah@example.com');
      expect(data.drafts.single.draftId, 'draft-abc');
      expect(data.sentHistory.single.repliedAt, isNull);
      expect(data.knownRecipients.single.messageCount, 1);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createEmailOverviewFetcher(getAccessToken: () async => null, client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
      expect(requestSent, isFalse);
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'detail': 'expired'}), 401));
      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw http.ClientException('Connection refused'));
      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('a 200 with an unparseable body throws a real ApiException, not a raw FormatException', () async {
      final client = MockClient((request) async => http.Response('not json at all', 200));
      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });

    test('a 200 with a missing required field throws ApiException, not a raw type error', () async {
      final client = MockClient((request) async => http.Response(jsonEncode({'drafts': []}), 200));
      final fetch = createEmailOverviewFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
