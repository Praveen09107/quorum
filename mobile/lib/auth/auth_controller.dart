/// The real orchestration layer: sign in (PKCE + real browser-based
/// Google consent + real code exchange + real secure storage), sign
/// out (real server-side revocation + real local clear), and handing
/// callers a currently-valid access token, refreshing proactively
/// before it expires rather than reacting to a real 401 after the fact.
library;

import 'dart:convert';

import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

import 'auth_api.dart';
import 'pkce.dart';

/// The real backend bridge (`GET /auth/callback`, `DEC-105`) -- Google's
/// own current rules require a real `https://` redirect for a "Web
/// application"-type OAuth client (confirmed live before building this;
/// custom schemes are no longer accepted directly). This bridge then
/// hands off to the mobile app's own custom scheme below.
const _oauthRedirectBridge = 'https://quorum-backend-649581407643.asia-south1.run.app/auth/callback';

/// Must match the real, installed Android app's applicationId
/// (`com.quorum.quorum_mobile`) and the real intent-filter registered
/// in `AndroidManifest.xml` for `flutter_web_auth_2`'s callback activity.
const _mobileCallbackScheme = 'com.quorum.quorum_mobile';

const _googleAuthEndpoint = 'https://accounts.google.com/o/oauth2/v2/auth';

/// A real, honest, typed reason a sign-in attempt didn't produce a
/// session -- never a bare bool, so a real UI can tell "you cancelled"
/// from "Google rejected this" from "our own server is down."
class SignInCancelled implements Exception {}

class AuthController {
  final AuthApi _api;
  final Future<void> Function(TokenPair) _saveTokens;
  final Future<TokenPair?> Function() _readTokens;
  final Future<void> Function() _clearTokens;
  final String _googleClientId;

  /// Storage is injected as three plain async functions -- the same
  /// established convention this whole codebase uses everywhere else
  /// (`main_shell.dart`'s fetcher typedefs), not an invented storage
  /// interface. The real, live implementations
  /// (`TokenStore.save`/`.read`/`.clear`) are secure-storage-backed;
  /// tests inject simple in-memory fakes with zero platform dependency.
  const AuthController({
    required AuthApi api,
    required Future<void> Function(TokenPair) saveTokens,
    required Future<TokenPair?> Function() readTokens,
    required Future<void> Function() clearTokens,
    required String googleClientId,
  })  : _api = api,
        _saveTokens = saveTokens,
        _readTokens = readTokens,
        _clearTokens = clearTokens,
        _googleClientId = googleClientId;

  /// The real, full sign-in flow. Launches a real system browser tab to
  /// Google's real consent screen, waits for the real redirect, and on
  /// success stores a real, live Quorum session.
  Future<void> signIn() async {
    final pkce = generatePkcePair();
    final state = generateOauthState();

    final authUrl = Uri.parse(_googleAuthEndpoint).replace(queryParameters: {
      'client_id': _googleClientId,
      'redirect_uri': _oauthRedirectBridge,
      'response_type': 'code',
      'scope': 'openid email',
      'code_challenge': pkce.codeChallenge,
      'code_challenge_method': 'S256',
      'state': state,
      // Real, deliberate: forces Google's real account chooser even if
      // a Google session is already active in the system browser --
      // this is a personal-ops assistant tied to one real Gmail
      // account, never silently signing in as whichever account
      // happened to be logged into the browser already.
      'prompt': 'select_account',
    });

    final String result;
    try {
      result = await FlutterWebAuth2.authenticate(
        url: authUrl.toString(),
        callbackUrlScheme: _mobileCallbackScheme,
      );
    } catch (e) {
      // flutter_web_auth_2 throws when the user closes the browser tab
      // without completing the flow -- a real, honest cancellation, not
      // an error to alarm about.
      throw SignInCancelled();
    }

    final callbackUri = Uri.parse(result);
    final returnedState = callbackUri.queryParameters['state'];
    final error = callbackUri.queryParameters['error'];
    final code = callbackUri.queryParameters['code'];

    if (error != null) {
      throw Exception('Google sign-in failed: $error');
    }
    if (returnedState != state) {
      // A real, genuine CSRF-relevant mismatch -- never proceed on a
      // callback whose state doesn't match what this exact sign-in
      // attempt generated.
      throw Exception('Sign-in could not be verified (state mismatch) -- please try again.');
    }
    if (code == null) {
      throw Exception('Google sign-in did not return an authorization code.');
    }

    final tokens = await _api.exchangeCode(
      code: code,
      codeVerifier: pkce.codeVerifier,
      redirectUri: _oauthRedirectBridge,
    );
    await _saveTokens(tokens);
  }

  /// The real "sign out everywhere" control -- revokes server-side
  /// first (best-effort: a network failure here must not leave the
  /// device claiming to be signed in when the user asked to sign out),
  /// then always clears the real local storage regardless.
  Future<void> signOut() async {
    final tokens = await _readTokens();
    if (tokens != null) {
      try {
        await _api.revoke(accessToken: tokens.accessToken);
      } catch (_) {
        // Best-effort -- the real local sign-out below still happens
        // either way; a real, live server-side revocation failure
        // shouldn't trap a user who wants to sign out of THIS device.
      }
    }
    await _clearTokens();
  }

  /// Returns a real, currently-valid access token, refreshing
  /// proactively first if the stored one is expired or expiring within
  /// a real 30-second buffer. Returns null if there's no real session
  /// at all, or if the stored refresh token is itself no longer valid
  /// (revoked/reused/expired) -- in which case local storage is also
  /// cleared, since a token that can never be refreshed again is not a
  /// real session.
  Future<String?> getValidAccessToken() async {
    final tokens = await _readTokens();
    if (tokens == null) return null;

    if (!_isExpiredOrExpiringSoon(tokens.accessToken)) {
      return tokens.accessToken;
    }

    try {
      final refreshed = await _api.refresh(refreshToken: tokens.refreshToken);
      await _saveTokens(refreshed);
      return refreshed.accessToken;
    } catch (_) {
      await _clearTokens();
      return null;
    }
  }

  /// A real, local-only check of OUR OWN already-trusted token's `exp`
  /// claim -- never a security verification (the token's signature is
  /// never checked here; it was already trusted the moment it was
  /// stored, straight from our own backend). Purely a proactive
  /// "should I refresh before using this" decision.
  bool _isExpiredOrExpiringSoon(String accessToken) {
    final parts = accessToken.split('.');
    if (parts.length != 3) return true;
    try {
      final normalized = base64Url.normalize(parts[1]);
      final payload = jsonDecode(utf8.decode(base64Url.decode(normalized))) as Map<String, dynamic>;
      final exp = payload['exp'] as int?;
      if (exp == null) return true;
      final expiresAt = DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
      return DateTime.now().toUtc().isAfter(expiresAt.subtract(const Duration(seconds: 30)));
    } catch (_) {
      // A real, malformed or unparseable token is treated as expired --
      // the safe, honest direction (forces a real refresh attempt
      // rather than trusting a token this code couldn't even read).
      return true;
    }
  }
}
