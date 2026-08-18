// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// The staged reveal, literally implemented, not just described: Stage A
// renders first, unconditionally. Stage B — findings from the genuinely
// more expensive, judgment-based layer — only appears in the widget tree
// at all if `stageBRan` is true, matching the Gate's own real
// architecture where S0/S1 actions never reach Stage B in the first
// place.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';

class GateRevealScreen extends StatelessWidget {
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const GateRevealScreen({
    super.key,
    required this.findings,
    required this.objections,
  });

  @override
  Widget build(BuildContext context) {
    final ranStageB = stageBRan(objections);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Stage A — automated checks', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final finding in findings) _FindingRow(finding: finding),
        // Stage B only ever appears in the widget tree if it genuinely
        // ran -- an S0/S1 action's screen simply has no Stage B section
        // at all, never an empty or misleading placeholder for one.
        if (ranStageB) ...[
          const SizedBox(height: 24),
          Text('Stage B — Critic review', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _StageBSection(summary: summarizeStageB(objections)),
        ],
      ],
    );
  }
}

class _FindingRow extends StatelessWidget {
  final FindingSummary finding;

  const _FindingRow({required this.finding});

  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (finding.visualState) {
      EvidenceVisualState.positive => (Icons.check_circle, QuorumStatusColors.verified),
      EvidenceVisualState.negative => (Icons.cancel, QuorumStatusColors.critical),
      EvidenceVisualState.uncertain => (Icons.help_outline, QuorumStatusColors.needsAttention),
    };

    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(finding.claim),
      subtitle: Text(finding.validator),
    );
  }
}

class _StageBSection extends StatelessWidget {
  final StageBSummary summary;

  const _StageBSection({required this.summary});

  @override
  Widget build(BuildContext context) {
    if (summary.realObjections.isEmpty) {
      // Stage B genuinely ran and signed off -- a real, positive
      // outcome, never rendered as "nothing happened."
      return const ListTile(
        leading: Icon(Icons.verified, color: QuorumStatusColors.verified),
        title: Text('Reviewed — no objections'),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final objection in summary.realObjections)
          ListTile(
            leading: const Icon(Icons.flag, color: QuorumStatusColors.needsAttention),
            title: Text(objection.description),
            subtitle: Text('${objection.category} · ${objection.severity}'),
          ),
      ],
    );
  }
}
