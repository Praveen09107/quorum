// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Structurally correct against plain `package:test`'s
// documented API — deliberately not `flutter_test`, since this file has
// zero Flutter framework dependency (pure config/logic), so it runs via
// plain `dart test` rather than needing the full `flutter test` harness,
// per this project's own documented distinction (CLAUDE.md). `dart test`
// on a real machine is the actual verification.
//
// Boundary values below were hand-verified in Python before this file
// was finalized (this sandbox can run Python, not Dart) — see
// DECISIONS_LOG.md for the real, executed reimplementation confirming
// every boundary (8192, 8191, 4096, 4095, 512) matches
// classifyDeviceTier's real logic line for line.

import 'package:test/test.dart';

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
        'resolvedFullTierModel is genuinely resolved -- real Sprint 0 result, DEC-130',
        () {
      // THE real, load-bearing check: a regression here would mean this
      // project silently guessed at an empirical question it explicitly
      // committed to resolving only by real measurement. Now asserting
      // the actual, real, mechanically-decided outcome: Sprint 0 genuinely
      // ran to completion on a real device, Llama 3.2 3B genuinely
      // downloaded, loaded, and passed real on-device inference (67%
      // validity) -- a real winner, not the StateError fallback path.
      expect(resolvedFullTierModel, OnDeviceModelId.llama32_3B);
    });
  });

  group('resolveModelForTier', () {
    test('resolves Full tier to the real, decided Llama 3.2 3B winner',
        () {
      expect(resolveModelForTier(DeviceTier.full), 'Llama 3.2 3B');
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
