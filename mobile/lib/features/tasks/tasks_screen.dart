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

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/predictive_risk/predictive_risk_logic.dart';
import 'package:quorum_mobile/features/tasks/tasks_logic.dart';

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
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: sorted.length,
            itemBuilder: (context, index) {
              final task = sorted[index];
              return Card(
                child: ListTile(
                  title: Text(task.title),
                  subtitle: Text(
                    task.deadline == null
                        ? formatHours(task.estimatedHours)
                        : '${formatHours(task.estimatedHours)} · due ${task.deadline!.toIso8601String().split('T').first}',
                  ),
                  trailing: Chip(label: Text(statusLabel(task.status))),
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
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Card(
            color: risk.isAtRisk ? Theme.of(context).colorScheme.errorContainer : null,
            child: ListTile(
              leading: Icon(risk.isAtRisk ? Icons.warning_amber_rounded : Icons.check_circle_outline),
              title: Text(riskMessage(risk)),
            ),
          ),
        );
      },
    );
  }
}
