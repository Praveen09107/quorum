// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Zero Flutter dependencies (same as the file under
// test) — plain `package:test`, `dart test` is the real verification.
//
// The rounding boundary test below (0.999 -> 100%) is deliberately a
// genuinely unambiguous case, hand-verified in Python before being
// trusted here: 0.999 * 100 = 99.9, which rounds to 100 under EITHER
// rounding convention. The exact .5 tie case (e.g. 0.505 * 100 = 50.5,
// where Python's banker's rounding and Dart's round-half-away-from-zero
// disagree) is deliberately NOT tested here — see DECISIONS_LOG.md and
// STATUS_INDEX.md's open item on this exact, still-open uncertainty.

import 'package:test/test.dart';

import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';

void main() {
  group('metricLabel -- the real, closed three-metric set', () {
    test('deadline_slack_hours gets a real, distinct label', () {
      expect(metricLabel('deadline_slack_hours'), 'Deadline slack');
    });

    test('budget_remaining_fraction gets a real, distinct label', () {
      expect(metricLabel('budget_remaining_fraction'), 'Budget remaining');
    });

    test('task_hours_committed gets a real, distinct label', () {
      expect(metricLabel('task_hours_committed'), 'Hours committed');
    });
  });

  group('formatMetricValue -- unit-correctness, not generic formatting', () {
    test('deadline_slack_hours renders with a real "h" suffix', () {
      expect(formatMetricValue('deadline_slack_hours', 3.5), '3.5h');
    });

    test('task_hours_committed also renders with a real "h" suffix', () {
      expect(formatMetricValue('task_hours_committed', 12.0), '12.0h');
    });

    test('budget_remaining_fraction renders as a real percentage, never as a raw fraction or hours', () {
      final result = formatMetricValue('budget_remaining_fraction', 0.25);
      expect(result, '25%');
      expect(result.contains('h'), isFalse);
    });

    test('the real, hand-verified, unambiguous rounding boundary: 0.999 rounds to 100%, not truncated to 99%', () {
      expect(formatMetricValue('budget_remaining_fraction', 0.999), '100%');
    });

    // The real, exact `.5` tie case (STATUS_INDEX.md open item #11),
    // resolved live against a real Dart compiler this session: Dart's
    // num.round() is round-half-AWAY-FROM-ZERO, confirmed directly
    // (0.505 * 100 == 50.5, .round() == 51) -- genuinely different from
    // Python's banker's rounding, which would give 50. This was
    // deliberately left unasserted until a real compiler could confirm
    // it, per this file's own established discipline.
    test('the real, now-confirmed .5 tie: 0.505 rounds to 51%, round-half-away-from-zero', () {
      expect(formatMetricValue('budget_remaining_fraction', 0.505), '51%');
    });
  });

  group('visualStateForDirection -- trusts the backend, the direct DEC-070-connected dependency', () {
    test('improves maps to the real improves visual state', () {
      expect(visualStateForDirection('improves'), MetricVisualDirection.improves);
    });

    test('worsens maps to the real worsens visual state', () {
      expect(visualStateForDirection('worsens'), MetricVisualDirection.worsens);
    });

    test('unchanged maps to the real unchanged visual state', () {
      expect(visualStateForDirection('unchanged'), MetricVisualDirection.unchanged);
    });

    test('an unrecognized direction value defensively falls back to unchanged, never a crash', () {
      expect(visualStateForDirection('something_new'), MetricVisualDirection.unchanged);
    });
  });

  group('capitalizeDomain', () {
    test('capitalizes a real lowercase domain string', () {
      expect(capitalizeDomain('calendar'), 'Calendar');
      expect(capitalizeDomain('finance'), 'Finance');
      expect(capitalizeDomain('tasks'), 'Tasks');
    });

    test('an empty string is handled without throwing', () {
      expect(capitalizeDomain(''), '');
    });
  });

  test('end-to-end: all three real metrics render correctly together for one option\'s full impact', () {
    // Confirms the whole real closed metric set is handled without a
    // gap when exercised together, not just individually.
    final impact = [
      const ImpactDeltaData(metric: 'deadline_slack_hours', before: 5.0, after: 3.0, direction: 'worsens'),
      const ImpactDeltaData(metric: 'budget_remaining_fraction', before: 0.5, after: 0.6, direction: 'improves'),
      const ImpactDeltaData(metric: 'task_hours_committed', before: 10.0, after: 10.0, direction: 'unchanged'),
    ];

    final rendered = impact
        .map((d) => '${metricLabel(d.metric)}: ${formatMetricValue(d.metric, d.before)} -> ${formatMetricValue(d.metric, d.after)} (${visualStateForDirection(d.direction).name})')
        .toList();

    expect(rendered[0], 'Deadline slack: 5.0h -> 3.0h (worsens)');
    expect(rendered[1], 'Budget remaining: 50% -> 60% (improves)');
    expect(rendered[2], 'Hours committed: 10.0h -> 10.0h (unchanged)');
  });
}
