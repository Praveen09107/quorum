// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// All three boundary cases hand-verified in Python before this file was
// finalized:
//   3 rapid failures triggers: True
//   2 failures at exactly 2min triggers: True (inclusive boundary)
//   2 failures under 2min triggers: False

import 'package:test/test.dart';

import 'package:quorum_mobile/features/outage/outage_detector.dart';

final _t0 = DateTime(2026, 1, 1, 12, 0, 0);

void main() {
  test('3 rapid consecutive failures trigger an outage via the count threshold', () {
    var state = OutageState.initial;
    for (var i = 0; i < 3; i++) {
      state = recordFailure(state, _t0.add(Duration(seconds: i)));
    }
    expect(state.isInOutage, isTrue);
  });

  test('2 failures spanning exactly the 2-minute duration threshold trigger an outage (inclusive boundary)', () {
    var state = OutageState.initial;
    state = recordFailure(state, _t0);
    state = recordFailure(state, _t0.add(const Duration(minutes: 2)));
    expect(state.isInOutage, isTrue);
  });

  test('2 failures spanning just under the 2-minute threshold do NOT trigger', () {
    var state = OutageState.initial;
    state = recordFailure(state, _t0);
    state = recordFailure(state, _t0.add(const Duration(minutes: 1, seconds: 59)));
    expect(state.isInOutage, isFalse);
  });

  test('a single failure alone, below both thresholds, does not trigger', () {
    final state = recordFailure(OutageState.initial, _t0);
    expect(state.isInOutage, isFalse);
    expect(state.consecutiveFailures, 1);
  });

  test('consecutiveFailures increments by exactly one per real recorded failure', () {
    var state = OutageState.initial;
    state = recordFailure(state, _t0);
    state = recordFailure(state, _t0.add(const Duration(seconds: 1)));
    expect(state.consecutiveFailures, 2);
  });

  test('unreachableSince is set on the first failure and stays fixed across subsequent failures', () {
    var state = OutageState.initial;
    state = recordFailure(state, _t0);
    final firstUnreachable = state.unreachableSince;
    state = recordFailure(state, _t0.add(const Duration(seconds: 30)));
    expect(state.unreachableSince, firstUnreachable);
  });

  test('a real success genuinely resets the WHOLE state, not a gradual recovery', () {
    var state = OutageState.initial;
    for (var i = 0; i < 3; i++) {
      state = recordFailure(state, _t0.add(Duration(seconds: i)));
    }
    expect(state.isInOutage, isTrue);

    state = recordSuccess(state);

    expect(state.isInOutage, isFalse);
    expect(state.consecutiveFailures, 0);
    expect(state.unreachableSince, isNull);
  });

  test('a real failure arriving after outage mode is already active never un-triggers it', () {
    var state = OutageState.initial;
    for (var i = 0; i < 3; i++) {
      state = recordFailure(state, _t0.add(Duration(seconds: i)));
    }
    expect(state.isInOutage, isTrue);

    state = recordFailure(state, _t0.add(const Duration(seconds: 10)));
    expect(state.isInOutage, isTrue);
  });

  test('the real initial state has isInOutage false and zero failures', () {
    expect(OutageState.initial.isInOutage, isFalse);
    expect(OutageState.initial.consecutiveFailures, 0);
    expect(OutageState.initial.unreachableSince, isNull);
  });
}
