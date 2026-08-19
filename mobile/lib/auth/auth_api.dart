/// The real, live client for the backend's three real auth routes
/// (`POST /auth/token`, `/auth/refresh`, `/auth/revoke` -- `DEC-101`).
/// Matches `main.py`'s own real request/response schemas exactly
/// (`TokenExchangeRequest`, `RefreshRequest`, `TokenPairResponse`),
/// confirmed directly from the real, live backend source before
/// writing this file, not guessed.

library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:quorum_mobile/api/api_exceptions.dart';
import 'package:quorum_mobile/config/api_config.dart';

class TokenPair {
  final String accessToken;
  final String refreshToken;

  const TokenPair({required this.accessToken, required this.refreshToken});
}

class AuthApi {
  final http.Client client;
  final String baseUrl;

  const AuthApi({required this.client, this.baseUrl = ApiConfig.baseUrl});

  /// `redirect_uri` here must be the SAME real value used in the
  /// original Google authorization request -- the real backend's own
  /// `GET /auth/callback` bridge URL, never the mobile app's custom
  /// scheme (Google's token endpoint validates the two match).
  Future<TokenPair> exchangeCode({
    required String code,
    required String codeVerifier,
    required String redirectUri,
  }) async {
    final response = await client.post(
      Uri.parse('$baseUrl/auth/token'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'code': code, 'code_verifier': codeVerifier, 'redirect_uri': redirectUri}),
    );
    return _parseTokenPairOrThrow(response, authFailureMessage: 'Sign-in failed -- please try again.');
  }

  Future<TokenPair> refresh({required String refreshToken}) async {
    final response = await client.post(
      Uri.parse('$baseUrl/auth/refresh'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refreshToken}),
    );
    return _parseTokenPairOrThrow(response, authFailureMessage: 'Your session has expired -- please sign in again.');
  }

  /// The real "sign out everywhere" control. Requires a real, currently
  /// valid access token -- the backend derives WHOSE sessions to revoke
  /// from that token, never from a bare user id the caller could forge.
  Future<void> revoke({required String accessToken}) async {
    final response = await client.post(
      Uri.parse('$baseUrl/auth/revoke'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
    if (response.statusCode != 204) {
      throw ApiException('Could not sign out cleanly.', statusCode: response.statusCode);
    }
  }

  TokenPair _parseTokenPairOrThrow(http.Response response, {required String authFailureMessage}) {
    if (response.statusCode == 401) {
      throw ApiException(authFailureMessage, statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw ApiException('A real error occurred talking to Quorum: ${response.body}', statusCode: response.statusCode);
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return TokenPair(accessToken: json['access_token'] as String, refreshToken: json['refresh_token'] as String);
  }
}
