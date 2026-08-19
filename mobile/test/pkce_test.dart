// Real tests for auth/pkce.dart -- zero Flutter dependency, `dart test`
// is the real verification.

import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/auth/pkce.dart';

void main() {
  group('generatePkcePair', () {
    test('the real code_challenge is genuinely the SHA-256 S256 hash of the real code_verifier', () {
      // The real, load-bearing security property -- if this doesn't
      // hold, Google's own token endpoint will reject every real
      // exchange with a PKCE verification failure.
      final pair = generatePkcePair();
      final expectedChallenge = base64Url.encode(sha256.convert(utf8.encode(pair.codeVerifier)).bytes).replaceAll('=', '');
      expect(pair.codeChallenge, expectedChallenge);
    });

    test('the real code_verifier has no base64 padding characters, per RFC 7636', () {
      final pair = generatePkcePair();
      expect(pair.codeVerifier.contains('='), isFalse);
    });

    test('the real code_challenge has no base64 padding characters either', () {
      final pair = generatePkcePair();
      expect(pair.codeChallenge.contains('='), isFalse);
    });

    test('the real code_verifier is at least 43 characters, the RFC 7636 minimum', () {
      final pair = generatePkcePair();
      expect(pair.codeVerifier.length, greaterThanOrEqualTo(43));
    });

    test('two real, separate calls produce two genuinely different verifiers', () {
      // A real, meaningful randomness check -- not a formal statistical
      // proof, but a real, live confirmation this isn't accidentally
      // deterministic.
      final a = generatePkcePair();
      final b = generatePkcePair();
      expect(a.codeVerifier, isNot(b.codeVerifier));
      expect(a.codeChallenge, isNot(b.codeChallenge));
    });
  });

  group('generateOauthState', () {
    test('two real, separate calls produce two genuinely different state values', () {
      expect(generateOauthState(), isNot(generateOauthState()));
    });

    test('a real state value has no base64 padding characters', () {
      expect(generateOauthState().contains('='), isFalse);
    });
  });
}
