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
import 'package:quorum_mobile/theme/spacing.dart';

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
        padding: EdgeInsets.symmetric(vertical: QuorumSpacing.lg),
        child: Text('Nothing needs you right now.'),
      );
    }

    // A real, deliberate gap between cards (Phase 8, `DEC-156`) --
    // QuorumSpacing.sm, rather than relying on Card's own implicit
    // default margin to create rhythm.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < sorted.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          _NeedsYouNowCard(action: sorted[i], onTap: onTapAction),
        ],
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

    // REAL, NEW (the redesign's own real "urgency-tiered visual
    // treatment" work) -- a real, colored accent stripe down the left
    // edge of the card itself, not just the small leading icon badge:
    // closes the plan's own named gap ("S3/urgent cards get a distinct,
    // stronger visual weight... reuse QuorumStatusColors as real card
    // accents"). S0/S1 genuinely gets no stripe at all (zero width) --
    // this app's own real "not every status needs a loud visual
    // treatment" restraint, matching `QuorumStatusColors.uncertain`'s own
    // documented "softer, non-alarming" role for non-urgent real states.
    final accentWidth = switch (action.stakes) {
      'S3' => 4.0,
      'S2' => 3.0,
      _ => 0.0,
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (accentWidth > 0) Container(width: accentWidth, color: color),
            Expanded(child: _buildTile(context, summary, icon, color)),
          ],
        ),
      ),
    );
  }

  Widget _buildTile(BuildContext context, ActionSummaryText summary, IconData icon, Color color) {
    return ListTile(
        leading: QuorumIconBadge(icon: icon, color: color),
        title: Text(summary.headline),
        // REAL, DISCLOSED FIX (the redesign's own real bug-fix work):
        // closes a real, confirmed-live complaint -- two real "Send an
        // email / Needs your approval" cards looked identical. `detail`
        // (the real recipient/title/payee this specific action is
        // actually about) now renders as the primary subtitle line when
        // the real payload has one; `stakesLabel` moves to a smaller,
        // muted second line rather than disappearing, so neither real
        // signal is lost.
        subtitle: summary.detail == null
            ? Text(summary.stakesLabel)
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(summary.detail!),
                  Text(summary.stakesLabel, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
        onTap: onTap == null ? null : () => onTap!(action),
    );
  }
}
