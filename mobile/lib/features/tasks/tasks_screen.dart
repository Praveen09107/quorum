// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// `fetchPredictiveRisk` (Phase 6, `DEC-149`) is a real, deliberately
// minimal mobile surface for `features/predictive_risk.py` -- no prior
// spec contract named a screen for this feature at all (see that
// module's own top-of-file docstring for the full account). A small,
// separate banner ABOVE the real task list, not blocking it: a slow or
// failed risk fetch degrades gracefully to simply showing no banner,
// never breaking the one thing this screen already reliably does
// (showing real tasks).
//
// Phase 8 Session 3 (`DEC-157`) real componentry pass: each task row's
// leading icon now signals status by SHAPE (a real, closed
// `TaskStatus` enum -- confirmed safe to switch on exhaustively, unlike
// Career Pipeline's genuinely open `applications.status`), with
// `TaskStatus.done` also getting `QuorumStatusColors.verified` as a
// distinct color -- a real, completed task is a genuinely positive
// outcome worth visually distinguishing, the same way this app's other
// screens never let a positive/neutral/negative signal look identical.
// Open and cancelled share the same neutral tone, distinguished only by
// icon shape -- neither is a "good" or "bad" state on its own.
//
// A real, disclosed fix found while applying the new status-color system
// properly, not a pure reskin: `_PredictiveRiskBanner` previously
// silently collapsed THREE real, distinct states (genuinely not enough
// historical data yet; a real predicted busy week; a real all-clear)
// into just two visual treatments -- "not enough data" rendered
// identically to "all clear" (both plain, no color). That is exactly the
// `no_data_found`-collapsed-into-a-pass mistake this project's own
// `evidence_state` discipline (`CLAUDE.md`) exists to prevent elsewhere;
// there was no reason this screen should be the one exception. Now: no
// history -> `needsAttention` (a genuine ambiguity, matching that
// color's own documented meaning exactly); a real predicted busy week ->
// `uncertain` (a real, non-alarming heads-up, not a confirmed failure);
// a real all-clear -> `verified`. `riskMessage()`'s own three-way logic
// is untouched -- only which icon/color the UI selects around the same
// real message changed.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class TasksScreen extends StatelessWidget {
  final List<TaskData> tasks;
  final Future<RiskAssessmentData> Function()? fetchPredictiveRisk;

  const TasksScreen({super.key, required this.tasks, this.fetchPredictiveRisk});

  @override
  Widget build(BuildContext context) {
    final sorted = sortTasks(tasks);
    final riskFetch = fetchPredictiveRisk;

    if (sorted.isEmpty) {
      return Column(
        children: [
          if (riskFetch != null) _PredictiveRiskBanner(fetch: riskFetch),
          const Expanded(child: Center(child: Text('No tasks yet.'))),
        ],
      );
    }

    return Column(
      children: [
        if (riskFetch != null) _PredictiveRiskBanner(fetch: riskFetch),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.all(QuorumSpacing.md),
            itemCount: sorted.length,
            separatorBuilder: (_, __) => const SizedBox(height: QuorumSpacing.sm),
            itemBuilder: (context, index) {
              final task = sorted[index];
              final onSurfaceVariant = Theme.of(context).colorScheme.onSurfaceVariant;
              final (icon, color) = switch (task.status) {
                TaskStatus.done => (Icons.check_circle, QuorumStatusColors.verified),
                TaskStatus.open => (Icons.radio_button_unchecked, onSurfaceVariant),
                TaskStatus.cancelled => (Icons.cancel, onSurfaceVariant),
              };
              return Card(
                child: ListTile(
                  leading: QuorumIconBadge(icon: icon, color: color),
                  title: Text(task.title),
                  subtitle: Text(
                    task.deadline == null
                        ? formatHours(task.estimatedHours)
                        : '${formatHours(task.estimatedHours)} · due ${task.deadline!.toIso8601String().split('T').first}',
                  ),
                  trailing: Chip(
                    label: Text(statusLabel(task.status)),
                    backgroundColor: color.withValues(alpha: 0.12),
                    labelStyle: TextStyle(color: color),
                    side: BorderSide.none,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

/// A real, deliberately quiet loading/error state: this banner is a
/// bonus on top of the real task list, never something worth spinning
/// or erroring loudly over. Loading and error states both render as
/// nothing at all -- only a real, successfully-fetched assessment ever
/// shows a real message.
class _PredictiveRiskBanner extends StatelessWidget {
  final Future<RiskAssessmentData> Function() fetch;

  const _PredictiveRiskBanner({required this.fetch});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<RiskAssessmentData>(
      future: fetch(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done || snapshot.hasError || !snapshot.hasData) {
          return const SizedBox.shrink();
        }
        final risk = snapshot.data!;
        // Three real, distinct states -- see file header for why this
        // now matches the "never collapse a genuine ambiguity into a
        // pass or fail" discipline this project already applies
        // elsewhere.
        final (IconData icon, Color color) = risk.matchingHistoricalWeeks == 0
            ? (Icons.help_outline, QuorumStatusColors.needsAttention)
            : risk.isAtRisk
                ? (Icons.warning_amber_rounded, QuorumStatusColors.uncertain)
                : (Icons.check_circle_outline, QuorumStatusColors.verified);
        return Padding(
          padding: const EdgeInsets.fromLTRB(QuorumSpacing.md, QuorumSpacing.md, QuorumSpacing.md, 0),
          child: Card(
            child: ListTile(
              leading: QuorumIconBadge(icon: icon, color: color),
              title: Text(riskMessage(risk)),
            ),
          ),
        );
      },
    );
  }
}
