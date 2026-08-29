// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A direct, real connection to already-established design principles:
// stakes-proportional visual weight (ADD §12.4) is implemented as icon
// SHAPE changing (priority_high vs. info_outline) alongside color — never
// color alone — directly matching the accessibility rule already
// documented in quorum_theme.dart since MOBILE_01.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/today/needs_you_now_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';

class NeedsYouNowZone extends StatelessWidget {
  final List<PendingActionSummary> actions;
  final void Function(PendingActionSummary action)? onTapAction;

  const NeedsYouNowZone({
    super.key,
    required this.actions,
    this.onTapAction,
  });

  @override
  Widget build(BuildContext context) {
    final sorted = sortByUrgency(actions);

    if (sorted.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Text('Nothing needs you right now.'),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final action in sorted) _NeedsYouNowCard(action: action, onTap: onTapAction),
      ],
    );
  }
}

class _NeedsYouNowCard extends StatelessWidget {
  final PendingActionSummary action;
  final void Function(PendingActionSummary action)? onTap;

  const _NeedsYouNowCard({required this.action, this.onTap});

  @override
  Widget build(BuildContext context) {
    final summary = summarizeForNeedsYouNow(action);
    final colorScheme = Theme.of(context).colorScheme;

    // Stakes-proportional weight: icon SHAPE changes, not just color --
    // S3 gets a real attention-grabbing icon, S2 a milder one, S0/S1 a
    // purely informational one. Never color alone.
    //
    // S2 deliberately uses QuorumStatusColors.needsAttention, not
    // colorScheme.tertiary (`DEC-155` review finding) -- Phase 8 gave
    // `tertiary` a real, fixed meaning of its own (interactive emphasis /
    // primary call-to-action, see quorum_theme.dart), and reusing it here
    // would collide that meaning with this file's own, pre-existing
    // "S2 = needs your attention" signal. Reusing the real, already-
    // established semantic status color is the correct fix, not
    // inventing a third, parallel color system.
    final (icon, color) = switch (action.stakes) {
      'S3' => (Icons.priority_high, colorScheme.error),
      'S2' => (Icons.error_outline, QuorumStatusColors.needsAttention),
      _ => (Icons.info_outline, colorScheme.onSurfaceVariant),
    };

    return Card(
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(summary.headline),
        subtitle: Text(summary.stakesLabel),
        onTap: onTap == null ? null : () => onTap!(action),
      ),
    );
  }
}
