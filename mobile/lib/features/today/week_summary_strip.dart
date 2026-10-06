// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// REAL, NEW (the redesign's own real Today-screen work) -- "This week
// across your agents," the one glanceable cross-domain row the approved
// redesign plan named as the single biggest lever for "make all 5 agents
// visibly meaningful." A horizontally scrollable row of small stat
// cards, deliberately -- four real numbers side by side would cramp on
// a narrow real phone width (the same real `pumpAndSettle` screen-width
// constraint this app's other screens already design around), so this
// scrolls rather than squeezes.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/today/week_summary_logic.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class WeekSummaryStrip extends StatelessWidget {
  final Future<WeekSummaryData> Function()? fetch;

  const WeekSummaryStrip({super.key, this.fetch});

  @override
  Widget build(BuildContext context) {
    final fetcher = fetch;
    // The same honest "not yet connected" degrade every other optional
    // real fetcher in this app uses -- renders nothing at all rather
    // than a placeholder/dead strip.
    if (fetcher == null) return const SizedBox.shrink();

    return FutureBuilder<WeekSummaryData>(
      future: fetcher(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done || snapshot.hasError || !snapshot.hasData) {
          // A real, deliberately quiet degrade -- this strip is a bonus
          // on top of the real zones below it, never something worth
          // spinning or erroring loudly over (the same established
          // precedent `_PredictiveRiskBanner` in `tasks_screen.dart`
          // already set).
          return const SizedBox.shrink();
        }
        final data = snapshot.data!;
        return SizedBox(
          height: 92,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              _StatCard(icon: Icons.task_alt, text: formatTasksDueSummary(data.tasksDueThisWeek)),
              const SizedBox(width: QuorumSpacing.sm),
              _StatCard(icon: Icons.account_balance_wallet_outlined, text: formatSpendSummary(data)),
              const SizedBox(width: QuorumSpacing.sm),
              _StatCard(icon: Icons.work_outline, text: formatApplicationsSummary(data.applicationsInProgress)),
              const SizedBox(width: QuorumSpacing.sm),
              _StatCard(icon: Icons.mail_outline, text: formatWaitingOnSummary(data.waitingOnCount)),
            ],
          ),
        );
      },
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String text;

  const _StatCard({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 140,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(QuorumSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Theme.of(context).colorScheme.tertiary, size: 20),
              const SizedBox(height: QuorumSpacing.xs),
              Text(text, style: Theme.of(context).textTheme.bodySmall, maxLines: 2, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ),
    );
  }
}
