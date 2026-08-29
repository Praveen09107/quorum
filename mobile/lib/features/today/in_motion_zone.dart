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
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

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

    // A real, deliberate gap between cards (Phase 8, `DEC-156`), matching
    // `NeedsYouNowZone`'s own identical rhythm.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < sorted.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          _InMotionCard(negotiation: sorted[i], onTap: onTapNegotiation),
        ],
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
        // A neutral badge, not a status color -- a negotiation awaiting
        // choice isn't itself a verified/uncertain/critical signal in the
        // Gate's own sense, just a real, pending item. onSurfaceVariant
        // matches the same neutral tone `_NeedsYouNowCard` uses for its
        // own non-stakes-severity (S0/S1) icon, for consistency.
        leading: QuorumIconBadge(icon: Icons.sync_alt, color: Theme.of(context).colorScheme.onSurfaceVariant),
        title: Text(describeConflict(negotiation.conflictedDomains)),
        subtitle: const Text('Awaiting your choice'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap == null ? null : () => onTap!(negotiation.negotiationId),
      ),
    );
  }
}
