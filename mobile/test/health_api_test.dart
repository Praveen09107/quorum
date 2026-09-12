// Real tests for api/health_api.dart (QUORUM_PRODUCTION_READINESS_AUDIT_
// PLAN.md's own first audit run). Zero Flutter dependencies -- `dart
// test` is the real command, matching every other real `api/*.dart`
// test file's own established convention.

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/health_api.dart';

void main() {
  group('createHealthCheckCall', () {
    test('returns true on a real 200, and hits the real /health path with no auth header', () async {
      Uri? capturedUri;
      Map<String, String>? capturedHeaders;
      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedHeaders = request.headers;
        return http.Response('{"status": "ok"}', 200);
      });

      final healthCheck = createHealthCheckCall(client: client, baseUrl: 'https://example.test');
      final result = await healthCheck();

      expect(result, isTrue);
      expect(capturedUri.toString(), 'https://example.test/health');
      expect(capturedHeaders?.containsKey('Authorization'), isFalse);
    });

    test('returns false on a real non-200 response, never throws', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final healthCheck = createHealthCheckCall(client: client);

      expect(await healthCheck(), isFalse);
    });

    test('returns false on a genuine network failure, never throws', () async {
      final client = MockClient((request) async => throw Exception('no real connectivity'));
      final healthCheck = createHealthCheckCall(client: client);

      expect(await healthCheck(), isFalse);
    });

    test('returns false on a real timeout, never throws or hangs the caller', () async {
      final client = MockClient((request) async {
        await Future<void>.delayed(const Duration(seconds: 2));
        return http.Response('', 200);
      });
      final healthCheck = createHealthCheckCall(client: client, timeout: const Duration(milliseconds: 50));

      expect(await healthCheck(), isFalse);
    });
  });
}
