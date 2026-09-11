// Real tests for api/device_token_api.dart (`QUORUM_FINAL_COMPLETION_
// PLAN.md` Session 9, `DEC-176`). Zero Flutter dependencies -- `dart
// test` is the real command, matching `quick_capture_api_test.dart`'s
// own established convention exactly.

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/api/device_token_api.dart';

void main() {
  group('createDeviceTokenFetcher', () {
    test('sends the real Bearer header, the real base URL, and the real JSON body', () async {
      late Uri capturedUri;
      late String? capturedAuth;
      late Map<String, dynamic> capturedBody;

      final client = MockClient((request) async {
        capturedUri = request.url;
        capturedAuth = request.headers['Authorization'];
        capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response('{"status": "ok"}', 200);
      });

      final register = createDeviceTokenFetcher(
        getAccessToken: () async => 'a-real-test-token',
        client: client,
        baseUrl: 'https://example.test',
      );
      await register('a-real-fake-fcm-token');

      expect(capturedUri.toString(), 'https://example.test/device_token');
      expect(capturedAuth, 'Bearer a-real-test-token');
      expect(capturedBody, {'fcm_token': 'a-real-fake-fcm-token'});
    });

    test('a null access token fails loud with a real 401, before any real request is sent', () async {
      var requestSent = false;
      final client = MockClient((request) async {
        requestSent = true;
        return http.Response('', 200);
      });

      final register = createDeviceTokenFetcher(getAccessToken: () async => null, client: client);

      try {
        await register('a-real-fake-fcm-token');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 401);
      }
      expect(requestSent, isFalse);
    });

    test('a real 401 from the server surfaces as a real, distinct ApiException', () async {
      final client = MockClient((request) async => http.Response('', 401));
      final register = createDeviceTokenFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await register('a-real-fake-fcm-token');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 401);
      }
    });

    test('a real 422 throws a real, distinct ApiException', () async {
      final client = MockClient((request) async => http.Response('', 422));
      final register = createDeviceTokenFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await register('');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 422);
      }
    });

    test('a genuine network failure throws ApiException with a null statusCode', () async {
      final client = MockClient((request) async => throw Exception('no real connectivity'));
      final register = createDeviceTokenFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await register('a-real-fake-fcm-token');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, isNull);
      }
    });

    test('an unexpected status code throws with the real status code attached', () async {
      final client = MockClient((request) async => http.Response('', 503));
      final register = createDeviceTokenFetcher(getAccessToken: () async => 'token', client: client);

      try {
        await register('a-real-fake-fcm-token');
        fail('should have thrown');
      } on ApiException catch (e) {
        expect(e.statusCode, 503);
      }
    });
  });
}
