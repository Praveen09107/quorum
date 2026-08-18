// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real placement decision, not left to chance: the honesty label
// renders directly beneath the headline catch-rate number -- the same
// visual pass a person's eye makes reading the number itself, not small
// print at the screen's bottom where it could go unnoticed.
// QUORUM_DATA_CONTRACTS.md §5.14 calls this label load-bearing; this
// layout is built to actually treat it that way.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/trust/trust_logic.dart';

class TrustScreen extends StatelessWidget {
  final TrustData trust;

  const TrustScreen({super.key, required this.trust});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          formatCatchRate(trust.caught, trust.total),
          style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w600),
        ),
        // The load-bearing honesty label -- directly beneath the number,
        // not buried.
        Text(targetLabel(trust.target), style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 8),
        Text('${trust.caught} of ${trust.total} adversarial scenarios caught'),
        const SizedBox(height: 24),
        if (trust.missed.isNotEmpty) ...[
          Text('Missed', style: Theme.of(context).textTheme.titleSmall),
          for (final scenario in trust.missed)
            ListTile(
              leading: const Icon(Icons.warning_amber),
              title: Text('Scenario ${scenario.scenarioId}'),
              subtitle: Text('Expected ${scenario.expected}, got ${scenario.actual}'),
            ),
        ],
      ],
    );
  }
}
