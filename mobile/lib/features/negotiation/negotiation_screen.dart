// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Agent voices, rendered as genuinely distinct entries, not a single
// merged summary: each conflicted domain's real Position -- its concern
// and its own proposed resolution -- gets its own card, preserving the
// actual multi-agent structure.
//
// Every delta rendered with a real before -> after value, never just a
// direction arrow alone -- matching "the numbers are reproducible, only
// the narration is generative." This screen never asks the user to
// trust a symbol over the number backing it.
//
// Every option renders with IDENTICAL visual weight -- same card style,
// same button styling, no badge, no highlight, no ordering bias. This is
// the concrete implementation of the neutral-disclosure principle.
//
// Phase 8 Session 4 (`DEC-158`): `QuorumSpacing` tokens replace most
// literal values here, EXCEPT `_DeltaRow`'s own `vertical: 2`/`width: 6`
// -- both are deliberately finer-grained than `QuorumSpacing.xs` (4), a
// tight, intentional hairline gap for a compact inline delta row, not an
// oversight. Card-internal padding (`12`) is rounded up to
// `QuorumSpacing.md` (16), a real, disclosed 4px increase matching the
// same card-internal-padding precedent `holding_steady_zone.dart`
// already established, not a silent distortion.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/negotiation/negotiation_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class NegotiationScreen extends StatelessWidget {
  final List<PositionData> positions;
  final List<NegotiationOptionData> options;
  final void Function(String optionId)? onChoose;

  const NegotiationScreen({
    super.key,
    required this.positions,
    required this.options,
    this.onChoose,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        Text('What each domain is saying', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: QuorumSpacing.sm),
        for (final position in positions) _PositionCard(position: position),
        const SizedBox(height: QuorumSpacing.lg),
        Text('Your options', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: QuorumSpacing.sm),
        // Every option card below uses the exact same styling -- no
        // reordering, no highlighting, no badge on any one of them.
        for (final option in options) _OptionCard(option: option, onChoose: onChoose),
      ],
    );
  }
}

class _PositionCard extends StatelessWidget {
  final PositionData position;

  const _PositionCard({required this.position});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(capitalizeDomain(position.domain), style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: QuorumSpacing.xs),
            Text(position.concern),
            const SizedBox(height: QuorumSpacing.xs),
            Text('Proposes: ${position.proposedResolution}', style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _OptionCard extends StatelessWidget {
  final NegotiationOptionData option;
  final void Function(String optionId)? onChoose;

  const _OptionCard({required this.option, this.onChoose});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(option.description),
            const SizedBox(height: QuorumSpacing.sm),
            for (final delta in option.impact) _DeltaRow(delta: delta),
            const SizedBox(height: QuorumSpacing.sm),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                // Same button styling on every option -- no primary/
                // highlighted variant for any single one.
                onPressed: onChoose == null ? null : () => onChoose!(option.optionId),
                child: const Text('Choose this option'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DeltaRow extends StatelessWidget {
  final ImpactDeltaData delta;

  const _DeltaRow({required this.delta});

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (visualStateForDirection(delta.direction)) {
      MetricVisualDirection.improves => (Icons.trending_up, QuorumStatusColors.verified),
      MetricVisualDirection.worsens => (Icons.trending_down, QuorumStatusColors.critical),
      MetricVisualDirection.unchanged => (Icons.trending_flat, QuorumStatusColors.uncertain),
    };

    // Deliberately literal, not tokenized -- see file header: a
    // hairline gap finer than QuorumSpacing.xs, for a compact inline
    // row, not an oversight.
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 6),
          Expanded(child: Text(metricLabel(delta.metric))),
          // The real before -> after values, always shown alongside the
          // arrow -- never just the symbol alone.
          Text(
            '${formatMetricValue(delta.metric, delta.before)} → ${formatMetricValue(delta.metric, delta.after)}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
