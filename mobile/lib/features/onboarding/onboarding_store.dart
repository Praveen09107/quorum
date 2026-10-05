/// Real, on-device persistence of "has this real, signed-in user ever
/// completed onboarding." Deliberately backed by `flutter_secure_
/// storage`, the same real package `auth/token_store.dart` already
/// uses and this project's own real toolchain has already proven
/// builds successfully -- never a new package (e.g. `shared_
/// preferences`) for a single boolean flag. `main.dart`'s own header
/// comment already discloses the real, found risk class this avoids:
/// any new package carrying its own native Android build config is a
/// real toolchain risk on this project, confirmed live more than once
/// (`receive_sharing_intent`, `flutter_secure_storage` itself). A
/// non-secret boolean living in Keystore-backed storage is harmless
/// overkill, not a security concern -- there is nothing sensitive in
/// it.
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class OnboardingStore {
  static const _hasSeenOnboardingKey = 'quorum_has_seen_onboarding';

  final FlutterSecureStorage _storage;

  const OnboardingStore({FlutterSecureStorage? storage}) : _storage = storage ?? const FlutterSecureStorage();

  Future<bool> hasSeenOnboarding() async {
    final raw = await _storage.read(key: _hasSeenOnboardingKey);
    return raw == 'true';
  }

  Future<void> markSeen() async {
    await _storage.write(key: _hasSeenOnboardingKey, value: 'true');
  }
}
