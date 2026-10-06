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
//
// REAL, NEW (the redesign's own real "Finance hub" work) -- closes the
// approved plan's own named gap: "honestly, this screen is currently
// just a subscriptions detector with one item... redesign this screen
// into an actual Finance hub: a real budget bar at top..., a real
// recent-expenses list..., then the existing subscriptions section
// below." `monthToDateSpend`/`monthlyBudgetLimit`/`recentExpenses` are
// all real, optional, independently `null`-safe additions -- the
// existing subscriptions content is unchanged, just now one section
// among several rather than this screen's only content.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/theme/quorum_gauge.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class FinanceScreen extends StatelessWidget {
  final List<DetectedSubscriptionData> subscriptions;
  final double? monthToDateSpend;
  final double? monthlyBudgetLimit;
  final List<ExpenseData>? recentExpenses;

  const FinanceScreen({
    super.key,
    required this.subscriptions,
    this.monthToDateSpend,
    this.monthlyBudgetLimit,
    this.recentExpenses,
  });

  @override
  Widget build(BuildContext context) {
    final sorted = sortByAmountDesc(subscriptions);
    final spend = monthToDateSpend;
    final limit = monthlyBudgetLimit;
    final expenses = recentExpenses;

    final sections = <Widget>[
      if (spend != null && limit != null && limit > 0) _BudgetBar(spend: spend, limit: limit),
      if (expenses != null && expenses.isNotEmpty) _RecentExpensesSection(expenses: expenses),
      _SubscriptionsSection(subscriptions: sorted),
    ];

    return ListView.separated(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      itemCount: sections.length,
      separatorBuilder: (_, __) => const SizedBox(height: QuorumSpacing.lg),
      itemBuilder: (context, index) => sections[index],
    );
  }
}

/// A real, honest linear budget bar -- colored by real remaining
/// fraction, reusing `gaugeColorForFraction()`'s own already-established
/// three-tier semantics (the same real colors Today's own capacity/
/// budget gauges use) rather than a fourth, parallel color rule.
class _BudgetBar extends StatelessWidget {
  final double spend;
  final double limit;

  const _BudgetBar({required this.spend, required this.limit});

  @override
  Widget build(BuildContext context) {
    final remainingFraction = ((limit - spend) / limit).clamp(0.0, 1.0);
    final spentFraction = (spend / limit).clamp(0.0, 1.0);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(QuorumSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('This month', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: QuorumSpacing.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: spentFraction,
                minHeight: 10,
                backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                valueColor: AlwaysStoppedAnimation(gaugeColorForFraction(remainingFraction)),
              ),
            ),
            const SizedBox(height: QuorumSpacing.sm),
            Text(
              '${formatCurrency(spend)} of ${formatCurrency(limit)} spent',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _RecentExpensesSection extends StatelessWidget {
  final List<ExpenseData> expenses;

  const _RecentExpensesSection({required this.expenses});

  @override
  Widget build(BuildContext context) {
    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Recent expenses', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: QuorumSpacing.sm),
        for (var i = 0; i < expenses.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          Card(
            child: ListTile(
              leading: QuorumIconBadge(icon: Icons.receipt_long_outlined, color: badgeColor),
              title: Text(expenses[i].payee),
              subtitle: Text(_formatDate(expenses[i].occurredAt)),
              trailing: Text(formatCurrency(expenses[i].amount), style: QuorumTextStyles.metricSmall(context)),
            ),
          ),
        ],
      ],
    );
  }

  String _formatDate(DateTime date) => date.toIso8601String().split('T').first;
}

class _SubscriptionsSection extends StatelessWidget {
  final List<DetectedSubscriptionData> subscriptions;

  const _SubscriptionsSection({required this.subscriptions});

  @override
  Widget build(BuildContext context) {
    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;

    if (subscriptions.isEmpty) {
      return const Text('No recurring subscriptions detected.');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Subscriptions', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: QuorumSpacing.sm),
        for (var i = 0; i < subscriptions.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          Card(
            child: ListTile(
              leading: QuorumIconBadge(icon: Icons.autorenew, color: badgeColor),
              title: Text(subscriptions[i].payee),
              subtitle: Text(
                'Every ${formatInterval(subscriptions[i].averageIntervalDays)} · ${subscriptions[i].occurrences} charges seen',
              ),
              trailing: Text(
                formatCurrency(subscriptions[i].averageAmount),
                style: QuorumTextStyles.metricSmall(context),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
