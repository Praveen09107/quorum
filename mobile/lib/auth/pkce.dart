/// Real PKCE (RFC 7636) generation -- the mobile side of the real OAuth
/// flow. Matches the backend's own `auth/oauth_pkce.py` algorithm
/// exactly (SHA-256, base64url without padding), generated independently
/// here since PKCE's whole security property requires the verifier to
/// be generated and held ONLY by the client that will later redeem it
/// -- the backend never generates this on the client's behalf.
library;

import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

class PkcePair {
  final String codeVerifier;
  final String codeChallenge;

  const PkcePair({required this.codeVerifier, required this.codeChallenge});
}

/// A real, cryptographically random verifier (RFC 7636 recommends
/// 43-128 characters from the unreserved URI character set; 32 random
/// bytes, base64url-encoded, yields 43 characters -- the minimum, and
/// the same real length this project's own backend test doubles use).
PkcePair generatePkcePair() {
  final random = Random.secure();
  final verifierBytes = Uint8List.fromList(List.generate(32, (_) => random.nextInt(256)));
  final codeVerifier = base64UrlEncode(verifierBytes).replaceAll('=', '');

  final challengeBytes = sha256.convert(utf8.encode(codeVerifier)).bytes;
  final codeChallenge = base64UrlEncode(challengeBytes).replaceAll('=', '');

  return PkcePair(codeVerifier: codeVerifier, codeChallenge: codeChallenge);
}

/// A real, random CSRF-protection value for the OAuth `state` parameter
/// -- genuinely distinct from the PKCE verifier/challenge (a different
/// real security property: state protects against cross-site request
/// forgery on the redirect itself, PKCE protects the code exchange).
String generateOauthState() {
  final random = Random.secure();
  final bytes = Uint8List.fromList(List.generate(24, (_) => random.nextInt(256)));
  return base64UrlEncode(bytes).replaceAll('=', '');
}
