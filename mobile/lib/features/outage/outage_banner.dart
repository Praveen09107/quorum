// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Honest, specific language, not generic. This banner doesn't just say
// "you're offline" — it states the real, current policy: low-stakes
// actions queue, anything irreversible waits. A person reading it knows
// exactly what's actually happening to their pending actions, not just
// that a network problem exists somewhere.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/outage/outage_detector.dart';

class OutageBanner extends StatelessWidget {
  final OutageState state;

  const OutageBanner({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    if (!state.isInOutage) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      color: Theme.of(context).colorScheme.errorContainer,
      child: Row(
        children: [
          Icon(Icons.cloud_off, color: Theme.of(context).colorScheme.onErrorContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              "Connection lost. Low-stakes actions are queuing to send once you're back online; "
              'anything irreversible will wait for your explicit approval before it goes anywhere.',
              style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
