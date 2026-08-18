// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Deliberately minimal — a summary card per active negotiation, linking
// into the real interaction screen (MOBILE_09) rather than duplicating
// it here. This zone's whole job is a preview; the full negotiation
// interaction (agent voices, option cards, computed deltas) belongs to
// negotiation_screen.dart alone.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/today/in_motion_logic.dart';

class InMotionZone extends StatelessWidget {
  final List<ActiveNegotiationSummary> negotiations;
  final void Function(String negotiationId)? onTapNegotiation;

  const InMotionZone({
    super.key,
    required this.negotiations,
    this.onTapNegotiation,
  });

  @override
  Widget build(BuildContext context) {
    final sorted = sortByStaleness(negotiations);

    if (sorted.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final negotiation in sorted) _InMotionCard(negotiation: negotiation, onTap: onTapNegotiation),
      ],
    );
  }
}

class _InMotionCard extends StatelessWidget {
  final ActiveNegotiationSummary negotiation;
  final void Function(String negotiationId)? onTap;

  const _InMotionCard({required this.negotiation, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.sync_alt),
        title: Text(describeConflict(negotiation.conflictedDomains)),
        subtitle: const Text('Awaiting your choice'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap == null ? null : () => onTap!(negotiation.negotiationId),
      ),
    );
  }
}
