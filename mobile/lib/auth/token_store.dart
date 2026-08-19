/// Real, secure on-device storage for the real access/refresh token
/// pair -- backed by `flutter_secure_storage` (Android Keystore-backed
/// `EncryptedSharedPreferences`, never plain `SharedPreferences`). The
/// only place in this codebase that ever touches a raw token's value
/// beyond the moment it's used in an `Authorization` header.
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_api.dart';

class TokenStore {
  static const _accessTokenKey = 'quorum_access_token';
  static const _refreshTokenKey = 'quorum_refresh_token';

  final FlutterSecureStorage _storage;

  const TokenStore({FlutterSecureStorage? storage}) : _storage = storage ?? const FlutterSecureStorage();

  Future<void> save(TokenPair tokens) async {
    await _storage.write(key: _accessTokenKey, value: tokens.accessToken);
    await _storage.write(key: _refreshTokenKey, value: tokens.refreshToken);
  }

  /// Returns null if no real session is currently stored -- the honest
  /// "signed out" state, never a fabricated empty-string token.
  Future<TokenPair?> read() async {
    final access = await _storage.read(key: _accessTokenKey);
    final refresh = await _storage.read(key: _refreshTokenKey);
    if (access == null || refresh == null) return null;
    return TokenPair(accessToken: access, refreshToken: refresh);
  }

  Future<void> clear() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
  }
}
