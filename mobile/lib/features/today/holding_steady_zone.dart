// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Typography as the visualization, literally, not just in principle: the
// computed numbers render as large (36px, weight 600) numerals directly
// -- no chart widget, no gauge, no decorative graphic standing in for
// the number. The locked design principle from the ADD, implemented
// exactly as written.
//
// The F4 fix's UI requirement, honored to the letter: when a number's
// source is DataSource.localMirror, the card shows "Offline estimate"
// via BOTH an icon and text -- never color alone, matching the
// accessibility rule already established in quorum_theme.dart. This is
// the actual, concrete moment the ADD's "the client must render this
// label, never silently presenting one as the other" requirement
// becomes real UI, not just a documented promise.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/computed_state.dart';
import 'package:quorum_mobile/features/today/holding_steady_logic.dart';

class HoldingSteadyZone extends StatelessWidget {
  final CapacityState capacity;
  final BudgetState budget;
  final DateTime now;

  const HoldingSteadyZone({
    super.key,
    required this.capacity,
    required this.budget,
    required this.now,
  });

  @override
  Widget build(BuildContext context) {
    final touchpoint = classifyTouchpoint(now.hour);
    final headline = touchpointHeadline(touchpoint);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(headline, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            _ComputedNumberRow(
              label: 'Capacity remaining today',
              valueText: '${capacity.hoursRemainingToday.toStringAsFixed(1)}h',
              source: capacity.source,
            ),
            const SizedBox(height: 12),
            _ComputedNumberRow(
              label: 'Budget remaining this month',
              valueText: '${(budget.remainingFraction * 100).round()}%',
              source: budget.source,
            ),
          ],
        ),
      ),
    );
  }
}

class _ComputedNumberRow extends StatelessWidget {
  final String label;
  final String valueText;
  final DataSource source;

  const _ComputedNumberRow({
    required this.label,
    required this.valueText,
    required this.source,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodySmall),
              // Typography IS the visualization -- no chart, no gauge.
              Text(
                valueText,
                style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
        if (source == DataSource.localMirror) const _OfflineEstimateBadge(),
      ],
    );
  }
}

/// Never color alone -- both a real icon and real text, every time.
class _OfflineEstimateBadge extends StatelessWidget {
  const _OfflineEstimateBadge();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.cloud_off, size: 16, color: Theme.of(context).colorScheme.onSurfaceVariant),
        const SizedBox(width: 4),
        Text('Offline estimate', style: Theme.of(context).textTheme.labelSmall),
      ],
    );
  }
}
