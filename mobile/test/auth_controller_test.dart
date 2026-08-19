// Real tests for auth/auth_controller.dart's real refresh/sign-out
// logic. `signIn()` itself needs `flutter_web_auth_2`'s real platform
// channel (a real system browser), which this pure `dart test`
// environment cannot exercise -- the one real, human-completed
// verification this project's own established discipline already
// discloses as a standing limitation (no browser automation available).
// `getValidAccessToken()` and `signOut()` have zero platform dependency
// and are fully, genuinely tested here.

import 'dart:convert';

import 'package:test/test.dart';

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/auth/auth_api.dart';
import 'package:quorum_mobile/auth/auth_controller.dart';

/// A real, minimal JWT-SHAPED token (header.payload.signature) with a
/// controllable `exp` claim -- the signature segment is a real, fixed
/// placeholder, never verified by `AuthController` (that trust boundary
/// is the backend's own; this client-side check only ever reads the
/// `exp` claim to decide whether to proactively refresh).
String _fakeAccessToken({required DateTime expiresAt}) {
  final header = base64Url.encode(utf8.encode(jsonEncode({'alg': 'HS256', 'typ': 'JWT'}))).replaceAll('=', '');
  final payload = base64Url
      .encode(utf8.encode(jsonEncode({'sub': 'test-user', 'exp': expiresAt.toUtc().millisecondsSinceEpoch ~/ 1000})))
      .replaceAll('=', '');
  return '$header.$payload.fake-signature';
}

void main() {
  group('AuthController.getValidAccessToken', () {
    test('returns the real stored token unchanged when it is genuinely not close to expiring', () async {
      final freshToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(minutes: 10)));
      var refreshCalled = false;

      final controller = AuthController(
        api: _FakeAuthApi(onRefresh: () {
          refreshCalled = true;
          throw StateError('refresh should never be called here');
        }),
        saveTokens: (_) async {},
        readTokens: () async => TokenPair(accessToken: freshToken, refreshToken: 'real-refresh'),
        clearTokens: () async {},
        googleClientId: 'test-client-id',
      );

      final result = await controller.getValidAccessToken();

      expect(result, freshToken);
      expect(refreshCalled, isFalse);
    });

    test('proactively refreshes a real token that is expiring within the 30-second buffer', () async {
      final expiringToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(seconds: 10)));
      final refreshedToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(minutes: 15)));
      TokenPair? saved;

      final controller = AuthController(
        api: _FakeAuthApi(
          onRefresh: () async => TokenPair(accessToken: refreshedToken, refreshToken: 'new-refresh'),
        ),
        saveTokens: (tokens) async => saved = tokens,
        readTokens: () async => TokenPair(accessToken: expiringToken, refreshToken: 'old-refresh'),
        clearTokens: () async {},
        googleClientId: 'test-client-id',
      );

      final result = await controller.getValidAccessToken();

      expect(result, refreshedToken);
      expect(saved?.accessToken, refreshedToken);
    });

    test('proactively refreshes a real, already-expired token', () async {
      final expiredToken = _fakeAccessToken(expiresAt: DateTime.now().subtract(const Duration(minutes: 1)));
      final refreshedToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(minutes: 15)));

      final controller = AuthController(
        api: _FakeAuthApi(onRefresh: () async => TokenPair(accessToken: refreshedToken, refreshToken: 'new-refresh')),
        saveTokens: (_) async {},
        readTokens: () async => TokenPair(accessToken: expiredToken, refreshToken: 'old-refresh'),
        clearTokens: () async {},
        googleClientId: 'test-client-id',
      );

      expect(await controller.getValidAccessToken(), refreshedToken);
    });

    test('returns null with no real session stored, never attempting a refresh', () async {
      final controller = AuthController(
        api: _FakeAuthApi(onRefresh: () {
          throw StateError('refresh should never be called with no stored session');
        }),
        saveTokens: (_) async {},
        readTokens: () async => null,
        clearTokens: () async {},
        googleClientId: 'test-client-id',
      );

      expect(await controller.getValidAccessToken(), isNull);
    });

    test('a real failed refresh (revoked/reused/expired refresh token) clears storage and returns null', () async {
      final expiredToken = _fakeAccessToken(expiresAt: DateTime.now().subtract(const Duration(minutes: 1)));
      var cleared = false;

      final controller = AuthController(
        api: _FakeAuthApi(onRefresh: () async => throw const ApiException('refresh token revoked', statusCode: 401)),
        saveTokens: (_) async {},
        readTokens: () async => TokenPair(accessToken: expiredToken, refreshToken: 'dead-refresh'),
        clearTokens: () async => cleared = true,
        googleClientId: 'test-client-id',
      );

      final result = await controller.getValidAccessToken();

      expect(result, isNull);
      expect(cleared, isTrue);
    });

    test('a real, malformed stored token (not real JWT shape) is treated as expired, forcing a real refresh attempt', () async {
      final refreshedToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(minutes: 15)));

      final controller = AuthController(
        api: _FakeAuthApi(onRefresh: () async => TokenPair(accessToken: refreshedToken, refreshToken: 'new-refresh')),
        saveTokens: (_) async {},
        readTokens: () async => const TokenPair(accessToken: 'not-a-real-jwt', refreshToken: 'old-refresh'),
        clearTokens: () async {},
        googleClientId: 'test-client-id',
      );

      expect(await controller.getValidAccessToken(), refreshedToken);
    });
  });

  group('AuthController.signOut', () {
    test('genuinely revokes server-side then clears real local storage', () async {
      var revokedWithToken = '';
      var cleared = false;
      final activeToken = _fakeAccessToken(expiresAt: DateTime.now().add(const Duration(minutes: 10)));

      final controller = AuthController(
        api: _FakeAuthApi(onRevoke: (token) async => revokedWithToken = token),
        saveTokens: (_) async {},
        readTokens: () async => TokenPair(accessToken: activeToken, refreshToken: 'real-refresh'),
        clearTokens: () async => cleared = true,
        googleClientId: 'test-client-id',
      );

      await controller.signOut();

      expect(revokedWithToken, activeToken);
      expect(cleared, isTrue);
    });

    test('still clears real local storage even when the real server-side revoke call fails', () async {
      // A real, deliberate design property: a person asking to sign out
      // of THIS device must not be left "stuck" signed in just because
      // the network to the revoke endpoint happened to fail.
      var cleared = false;

      final controller = AuthController(
        api: _FakeAuthApi(onRevoke: (_) async => throw const ApiException('network down')),
        saveTokens: (_) async {},
        readTokens: () async => const TokenPair(accessToken: 'a-token', refreshToken: 'a-refresh'),
        clearTokens: () async => cleared = true,
        googleClientId: 'test-client-id',
      );

      await controller.signOut();

      expect(cleared, isTrue);
    });

    test('with no real session stored, does not attempt a revoke call at all, but still clears storage', () async {
      var revokeCalled = false;
      var cleared = false;

      final controller = AuthController(
        api: _FakeAuthApi(onRevoke: (_) async => revokeCalled = true),
        saveTokens: (_) async {},
        readTokens: () async => null,
        clearTokens: () async => cleared = true,
        googleClientId: 'test-client-id',
      );

      await controller.signOut();

      expect(revokeCalled, isFalse);
      expect(cleared, isTrue);
    });
  });
}

class _FakeAuthApi implements AuthApi {
  final Future<TokenPair> Function()? onRefresh;
  final Future<void> Function(String accessToken)? onRevoke;

  _FakeAuthApi({this.onRefresh, this.onRevoke});

  @override
  Future<TokenPair> exchangeCode({required String code, required String codeVerifier, required String redirectUri}) {
    throw UnimplementedError('not exercised by these real tests -- signIn() needs a real platform browser');
  }

  @override
  Future<TokenPair> refresh({required String refreshToken}) {
    return onRefresh?.call() ?? (throw StateError('onRefresh not configured for this test'));
  }

  @override
  Future<void> revoke({required String accessToken}) {
    return onRevoke?.call(accessToken) ?? Future.value();
  }

  @override
  String get baseUrl => throw UnimplementedError();

  @override
  get client => throw UnimplementedError();
}
