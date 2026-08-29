// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Most expensive subscription sorts first -- the most actionable
// ordering for a screen whose real purpose is helping someone decide
// what to cut.
//
// Phase 8 Session 3 (`DEC-157`): the trailing amount now uses
// `QuorumTextStyles.metricSmall()` (IBM Plex Mono, tabular figures) --
// this is exactly the "prominent numeric readout" that style family was
// built for, and tabular figures keep a column of real currency amounts
// visually aligned the way this list already invites comparing them. A
// neutral `Icons.autorenew` leading badge gives each row the same
// icon-badge visual language every other real list in this app now uses
// -- there's no per-subscription status to signal here (unlike Tasks'
// real, closed status set), so every row gets the identical neutral
// treatment rather than inventing a distinction that doesn't exist.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class FinanceScreen extends StatelessWidget {
  final List<DetectedSubscriptionData> subscriptions;

  const FinanceScreen({super.key, required this.subscriptions});

  @override
  Widget build(BuildContext context) {
    final sorted = sortByAmountDesc(subscriptions);

    if (sorted.isEmpty) {
      return const Center(child: Text('No recurring subscriptions detected.'));
    }

    return ListView.separated(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      itemCount: sorted.length,
      separatorBuilder: (_, __) => const SizedBox(height: QuorumSpacing.sm),
      itemBuilder: (context, index) {
        final subscription = sorted[index];
        return Card(
          child: ListTile(
            leading: QuorumIconBadge(
              icon: Icons.autorenew,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            title: Text(subscription.payee),
            subtitle: Text(
              'Every ${formatInterval(subscription.averageIntervalDays)} · ${subscription.occurrences} charges seen',
            ),
            trailing: Text(
              formatCurrency(subscription.averageAmount),
              style: QuorumTextStyles.metricSmall(context),
            ),
          ),
        );
      },
    );
  }
}
