// Real tests for api/today_api.dart. Zero Flutter dependencies, mirrors
// career_pipeline_api_test.dart/account_api_test.dart's own established
// pattern exactly -- package:http's MockClient, no separate mock
// library, `dart test` is the real verification.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/today_api.dart';
import 'package:quorum_mobile/features/computed_state.dart';

Map<String, dynamic> _realResponseBody() => {
      'capacity': {'hours_remaining_today': 5.0, 'remaining_fraction': 0.625, 'source': 'live_backend'},
      'budget': {'amount_remaining': 38000.0, 'remaining_fraction': 0.76, 'source': 'live_backend'},
      'needs_you_now': [
        {
          'proposal_id': 'a-real-proposal-id',
          'action_type': 'send_email',
          'stakes': 'S3',
          'payload': {'to': 'priya@x.com'},
          'created_at': '2026-08-20T14:00:00Z',
        },
      ],
      'in_motion': [
        {
          'negotiation_id': 'a-real-negotiation-id',
          'conflicted_domains': ['calendar', 'finance'],
          'started_at': '2026-08-20T09:00:00Z',
        },
      ],
    };

void main() {
  group('createTodayFetcher', () {
    test('sends a real GET request with the real Bearer header and the real base URL', () async {
      late Uri capturedUri;
      late String? capturedAuth;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        return http.Response(jsonEncode(_realResponseBody()), 200);
      });

      final fetch = createTodayFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await fetch();

      expect(capturedUri.toString(), 'https://example.test/today');
      expect(capturedAuth, 'Bearer a-real-test-token');
    });

    test('parses a real, complete 200 response into TodayScreenData -- every field', () async {
      final client = MockClient((request) async => http.Response(jsonEncode(_realResponseBody()), 200));
      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      final result = await fetch();

      expect(result.capacity.hoursRemainingToday, 5.0);
      expect(result.capacity.remainingFraction, 0.625);
      expect(result.capacity.source, DataSource.liveBackend);

      expect(result.budget.amountRemaining, 38000.0);
      expect(result.budget.remainingFraction, 0.76);
      expect(result.budget.source, DataSource.liveBackend);

      expect(result.pendingActions, hasLength(1));
      expect(result.pendingActions.first.proposalId, 'a-real-proposal-id');
      expect(result.pendingActions.first.actionType, 'send_email');
      expect(result.pendingActions.first.stakes, 'S3');
      expect(result.pendingActions.first.payload, {'to': 'priya@x.com'});
      expect(result.pendingActions.first.createdAt, DateTime.parse('2026-08-20T14:00:00Z'));

      expect(result.negotiations, hasLength(1));
      expect(result.negotiations.first.negotiationId, 'a-real-negotiation-id');
      expect(result.negotiations.first.conflictedDomains, ['calendar', 'finance']);
      expect(result.negotiations.first.startedAt, DateTime.parse('2026-08-20T09:00:00Z'));
    });

    test('a real, honest, currently-expected empty result parses correctly -- no producer pipeline exists yet', () async {
      final body = {
        'capacity': {'hours_remaining_today': 8.0, 'remaining_fraction': 1.0, 'source': 'live_backend'},
        'budget': {'amount_remaining': 50000.0, 'remaining_fraction': 1.0, 'source': 'live_backend'},
        'needs_you_now': <Map<String, dynamic>>[],
        'in_motion': <Map<String, dynamic>>[],
      };
      final client = MockClient((request) async => http.Response(jsonEncode(body), 200));
      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      final result = await fetch();

      expect(result.pendingActions, isEmpty);
      expect(result.negotiations, isEmpty);
      expect(result.capacity.hoursRemainingToday, 8.0);
    });

    test('an unrecognized source value fails CLOSED to localMirror, never silently claims live', () async {
      final body = {
        'capacity': {'hours_remaining_today': 8.0, 'remaining_fraction': 1.0, 'source': 'something_unrecognized'},
        'budget': {'amount_remaining': 50000.0, 'remaining_fraction': 1.0, 'source': 'live_backend'},
        'needs_you_now': <Map<String, dynamic>>[],
        'in_motion': <Map<String, dynamic>>[],
      };
      final client = MockClient((request) async => http.Response(jsonEncode(body), 200));
      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      final result = await fetch();

      expect(result.capacity.source, DataSource.localMirror);
    });

    test('a null access token (no real session) fails loud with a real 401, before any real request is even sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final fetch = createTodayFetcher(getAccessToken: () async => null, client: client);

      try {
        await fetch();
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.isAuthFailure, isTrue);
        expect(requestSent, isFalse);
      }
    });

    test('a real 401 from the server throws ApiException with isAuthFailure true', () async {
      final client = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Missing or malformed Authorization header'}), 401);
      });

      final fetch = createTodayFetcher(getAccessToken: () async => 'expired', client: client);

      try {
        await fetch();
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

      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
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

      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      try {
        await fetch();
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

      final fetch = createTodayFetcher(getAccessToken: () async => 't', client: client);

      await expectLater(fetch(), throwsA(isA<ApiException>()));
    });
  });
}
