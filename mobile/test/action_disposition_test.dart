// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// CRITICAL TIER, mirroring the file under test. The real, exhaustive
// 8-combination safety matrix was independently confirmed in Python
// before this file was finalized -- exactly one combination
// (S3, in outage) reaches blockUntilOnline.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/outage/action_disposition.dart';

void main() {
  test('THE SINGLE MOST CRITICAL CASE: S3 during an outage is blocked, never sent or queued', () {
    expect(decideDisposition('S3', true), ActionDisposition.blockUntilOnline);
  });

  test('THE FULL, EXHAUSTIVE 8-COMBINATION SAFETY MATRIX: exactly one path reaches blockUntilOnline', () {
    final results = <(String, bool), ActionDisposition>{};
    for (final stakes in ['S0', 'S1', 'S2', 'S3']) {
      for (final outage in [false, true]) {
        results[(stakes, outage)] = decideDisposition(stakes, outage);
      }
    }

    final blockingPaths = results.entries.where((e) => e.value == ActionDisposition.blockUntilOnline).map((e) => e.key).toList();

    expect(blockingPaths, [('S3', true)], reason: 'SAFETY ISSUE if this fails: an unexpected combination reaches blockUntilOnline, or S3+outage does not');
  });

  test('S0 online sends live', () {
    expect(decideDisposition('S0', false), ActionDisposition.sendLive);
  });

  test('S1 online sends live', () {
    expect(decideDisposition('S1', false), ActionDisposition.sendLive);
  });

  test('S2 online sends live', () {
    expect(decideDisposition('S2', false), ActionDisposition.sendLive);
  });

  test('S3 online sends live -- NOT blocked when the app is genuinely online, even though it is S3', () {
    expect(decideDisposition('S3', false), ActionDisposition.sendLive);
  });

  test('S0 during an outage queues locally, never blocked', () {
    expect(decideDisposition('S0', true), ActionDisposition.queueLocally);
  });

  test('S1 during an outage queues locally, never blocked', () {
    expect(decideDisposition('S1', true), ActionDisposition.queueLocally);
  });

  test('S2 during an outage queues locally, never blocked', () {
    expect(decideDisposition('S2', true), ActionDisposition.queueLocally);
  });
}
