/// `DEC-214` (product rebuild Part C, Priority 1) -- the real fix for
/// the most direct feedback this rebuild has gotten after the visual
/// redesign shipped: every structured write (Calendar booking, Task
/// create, Budget update, Application create, Interview schedule) was
/// ending in a flat `SnackBar`, even though the Gate's own real
/// `findings`/`objections` were already present in every single one of
/// those HTTP responses and simply never parsed or shown. The widgets
/// that make the Decision Trace screen genuinely compelling --
/// `FindingRow`/`StageBSection` -- already exist
/// (`gate_reveal_screen.dart`) and already work; this is the third real
/// reuse of them (after `scenario_verdict_screen.dart`), not a new
/// rendering.
///
/// The real `parseFindings`/`parseObjections` JSON parsing every API
/// client needs lives in the sibling, deliberately Flutter-free
/// `gate_verdict_parsing.dart` instead -- see that file's own
/// docstring for why the split exists. This file re-exports them so a
/// UI call site that needs both the parsing AND the rendering can
/// still import a single file.
library;

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/gate_reveal/gate_reveal_logic.dart';
import 'package:quorum_mobile/features/gate_reveal/gate_reveal_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

export 'package:quorum_mobile/features/gate_verdict/gate_verdict_parsing.dart';

/// The real decision-to-color/icon mapping every other real verdict
/// surface in this app already uses (`gate_reveal_screen.dart`'s own
/// terminal bar, `trust_screen.dart`'s scenario rows) -- repeated here
/// rather than imported, since neither of those exposes it as a public
/// function.
(IconData, Color) _decisionAppearance(String decision) {
  return switch (decision) {
    'approve' => (Icons.check_circle_rounded, QuorumDarkStatus.verified),
    'revise' => (Icons.edit_note_rounded, QuorumDarkStatus.needsAttention),
    'reject' => (Icons.cancel_rounded, QuorumDarkStatus.critical),
    'escalate_to_human' => (Icons.flag_rounded, QuorumDarkStatus.needsAttention),
    _ => (Icons.help_outline_rounded, QuorumDarkStatus.neutral),
  };
}

/// Opens the real "The Gate reviewed this" bottom sheet -- the one
/// call every structured-write flow in this app now makes right after
/// a genuine real submit, instead of going straight to a `SnackBar`.
Future<void> showGateVerdictSheet(
  BuildContext context, {
  required String decision,
  required String stakes,
  required List<FindingSummary> findings,
  required List<ObjectionSummary> objections,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _GateVerdictSheet(decision: decision, stakes: stakes, findings: findings, objections: objections),
  );
}

class _GateVerdictSheet extends StatelessWidget {
  final String decision;
  final String stakes;
  final List<FindingSummary> findings;
  final List<ObjectionSummary> objections;

  const _GateVerdictSheet({required this.decision, required this.stakes, required this.findings, required this.objections});

  @override
  Widget build(BuildContext context) {
    final (icon, color) = _decisionAppearance(decision);
    final stageBRanHere = stageBRanForStakes(stakes);

    // A plain, bounded-height scrollable sheet -- matching every other
    // real sheet in this app (`_SetBudgetSheet`/`_NewTaskSheet`/etc.),
    // none of which use `DraggableScrollableSheet`. That widget's own
    // drag-driven `AnimationController` never reaches Flutter test's
    // "no more frames scheduled" condition inside a modal route, so
    // `tester.pumpAndSettle()` never actually settles -- found live by
    // this entry's own widget tests before it shipped.
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85),
      child: Container(
        decoration: const BoxDecoration(
          color: QuorumDarkGround.raised,
          borderRadius: BorderRadius.vertical(top: Radius.circular(QuorumRadius.lg)),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(QuorumSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(icon, color: color, size: 28),
                  const SizedBox(width: QuorumSpacing.sm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('The Gate reviewed this', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: QuorumDarkGround.textPrimary)),
                        Text(_decisionLabel(decision), style: QuorumMono.detail(context, color: color)),
                      ],
                    ),
                  ),
                  StatusPill(label: stakes, icon: Icons.layers_outlined, color: color),
                  IconButton(
                    icon: const Icon(Icons.close, color: QuorumDarkGround.textSecondary),
                    tooltip: 'Done',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: QuorumSpacing.lg),
              if (findings.isEmpty)
                const HonestEmptyState(
                  icon: Icons.fact_check_outlined,
                  headline: 'No Stage A findings recorded',
                  detail: 'This real action genuinely had no validator checks to run against it.',
                )
              else ...[
                const SectionHeader(label: 'Stage A — what the real checks found'),
                for (final finding in findings) FindingRow(finding: finding),
              ],
              const SizedBox(height: QuorumSpacing.lg),
              if (stageBRanHere) ...[
                const SectionHeader(label: 'Stage B — the real Critic and Judge'),
                StageBSection(summary: summarizeStageB(objections)),
              ] else
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
                  child: Text(
                    'Stage B never ran — a real, structural fact for an S0/S1 proposal, not a gap.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textTertiary),
                  ),
                ),
              const SizedBox(height: QuorumSpacing.lg),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Done'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _decisionLabel(String decision) {
    return switch (decision) {
      'approve' => 'Approved',
      'revise' => 'Approved, revised by the Judge',
      'reject' => 'Rejected',
      'escalate_to_human' => 'Escalated for your review',
      _ => decision,
    };
  }
}
