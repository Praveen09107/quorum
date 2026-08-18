// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Structurally correct against `flutter_test`'s/
// `test` package's documented API; `flutter test` on a real machine is
// the actual verification.
//
// Boundary values below were hand-verified in Python before this file
// was finalized (this sandbox can run Python, not Dart) — see
// DECISIONS_LOG.md for the real, executed reimplementation confirming
// every boundary (8192, 8191, 4096, 4095, 512) matches
// classifyDeviceTier's real logic line for line.

import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/config/model_config.dart';
import 'package:quorum_mobile/model/device_tier.dart';
import 'package:quorum_mobile/model/on_device_model_loader.dart';

void main() {
  group('classifyDeviceTier real boundaries', () {
    test('exactly 8192MB is Full tier', () {
      expect(classifyDeviceTier(8192), DeviceTier.full);
    });

    test('8191MB, one below the Full boundary, is Light tier', () {
      expect(classifyDeviceTier(8191), DeviceTier.light);
    });

    test('exactly 4096MB is Light tier', () {
      expect(classifyDeviceTier(4096), DeviceTier.light);
    });

    test('4095MB, one below the Light boundary, is Cloud-only', () {
      expect(classifyDeviceTier(4095), DeviceTier.cloudOnly);
    });

    test('a very low-RAM device (512MB) is Cloud-only', () {
      expect(classifyDeviceTier(512), DeviceTier.cloudOnly);
    });
  });

  group('resolvedFullTierModel honesty', () {
    test(
        'resolvedFullTierModel is still genuinely unresolved -- Sprint 0 has not run',
        () {
      // THE real, load-bearing check: a regression here would mean this
      // project silently guessed at an empirical question it explicitly
      // committed to resolving only by real measurement.
      expect(resolvedFullTierModel, OnDeviceModelId.unresolved);
    });
  });

  group('resolveModelForTier', () {
    test(
        'throws OnDeviceModelNotResolvedException for Full tier while unresolved',
        () {
      expect(
        () => resolveModelForTier(DeviceTier.full),
        throwsA(isA<OnDeviceModelNotResolvedException>()),
      );
    });

    test('resolves the Light tier directly to the locked SmolLM2-1.7B model',
        () {
      expect(resolveModelForTier(DeviceTier.light), 'SmolLM2-1.7B');
    });

    test('returns null for Cloud-only -- no local model, by design, not an error',
        () {
      expect(resolveModelForTier(DeviceTier.cloudOnly), isNull);
    });
  });
}
