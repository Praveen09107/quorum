// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// Most expensive subscription sorts first -- the most actionable
// ordering for a screen whose real purpose is helping someone decide
// what to cut.
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
//
// `DEC-211` (product rebuild Part C, visual pass): redesigned onto the
// dark glassmorphic system `calendar_screen.dart`/`tasks_screen.dart`
// (`DEC-209`/`DEC-210`) already carry -- zero logic change (every real
// field stays independently optional exactly as before, `formatCurrency`/
// `formatInterval`/`sortByAmountDesc` untouched), every section's own
// real text content kept byte-for-byte identical to what
// `finance_screen_test.dart` already asserts.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/finance/finance_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_gauge.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
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
    final identity = identityOf(QuorumAgent.finance);
    final sorted = sortByAmountDesc(subscriptions);
    final spend = monthToDateSpend;
    final limit = monthlyBudgetLimit;
    final expenses = recentExpenses;

    final sections = <Widget>[
      if (spend != null && limit != null && limit > 0) _BudgetBar(spend: spend, limit: limit, accent: identity.accent),
      if (expenses != null && expenses.isNotEmpty) _RecentExpensesSection(expenses: expenses, accent: identity.accent),
      _SubscriptionsSection(subscriptions: sorted, accent: identity.accent),
    ];

    return QuorumAmbientBackground(
      accent: identity.accent,
      child: SafeArea(
        child: Padding(
          // Same real reason `calendar_screen.dart`/`tasks_screen.dart`
          // pad below the toolbar: this screen is PUSHED behind a
          // transparent, `extendBodyBehindAppBar: true` app bar kept
          // only for its real back button.
          padding: const EdgeInsets.only(top: kToolbarHeight - QuorumSpacing.md),
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(QuorumSpacing.md, 0, QuorumSpacing.md, QuorumSpacing.xxl),
            itemCount: sections.length + 1,
            separatorBuilder: (_, index) => index == 0 ? const SizedBox.shrink() : const SizedBox(height: QuorumSpacing.lg),
            itemBuilder: (context, index) => index == 0 ? _AgentHeader(identity: identity) : sections[index - 1],
          ),
        ),
      ),
    );
  }
}

class _AgentHeader extends StatelessWidget {
  final AgentIdentity identity;

  const _AgentHeader({required this.identity});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, QuorumSpacing.md, 0, QuorumSpacing.sm),
      child: Row(
        children: [
          const AgentBadge(agent: QuorumAgent.finance, compact: true),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(identity.name, style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
                Text(identity.purpose, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QuorumDarkGround.textSecondary)),
              ],
            ),
          ),
        ],
      ),
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
  final Color accent;

  const _BudgetBar({required this.spend, required this.limit, required this.accent});

  @override
  Widget build(BuildContext context) {
    final remainingFraction = ((limit - spend) / limit).clamp(0.0, 1.0);
    final spentFraction = (spend / limit).clamp(0.0, 1.0);
    return GlassPanel(
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('This month'.toUpperCase(), style: QuorumMono.label(context)),
          const SizedBox(height: QuorumSpacing.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: spentFraction,
              minHeight: 10,
              backgroundColor: QuorumDarkGround.surface,
              valueColor: AlwaysStoppedAnimation(gaugeColorForFraction(remainingFraction)),
            ),
          ),
          const SizedBox(height: QuorumSpacing.sm),
          Text(
            '${formatCurrency(spend)} of ${formatCurrency(limit)} spent',
            style: QuorumMono.detail(context, color: QuorumDarkGround.textPrimary),
          ),
        ],
      ),
    );
  }
}

class _RecentExpensesSection extends StatelessWidget {
  final List<ExpenseData> expenses;
  final Color accent;

  const _RecentExpensesSection({required this.expenses, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(label: 'Recent expenses', accent: accent),
        for (var i = 0; i < expenses.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          _Row(
            icon: Icons.receipt_long_outlined,
            title: expenses[i].payee,
            subtitle: _formatDate(expenses[i].occurredAt),
            trailing: formatCurrency(expenses[i].amount),
            accent: accent,
          ),
        ],
      ],
    );
  }

  String _formatDate(DateTime date) => date.toIso8601String().split('T').first;
}

class _SubscriptionsSection extends StatelessWidget {
  final List<DetectedSubscriptionData> subscriptions;
  final Color accent;

  const _SubscriptionsSection({required this.subscriptions, required this.accent});

  @override
  Widget build(BuildContext context) {
    if (subscriptions.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeader(label: 'Subscriptions', accent: accent),
          const Text('No recurring subscriptions detected.', style: TextStyle(color: QuorumDarkGround.textSecondary)),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(label: 'Subscriptions', accent: accent),
        for (var i = 0; i < subscriptions.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          _Row(
            icon: Icons.autorenew,
            title: subscriptions[i].payee,
            subtitle: 'Every ${formatInterval(subscriptions[i].averageIntervalDays)} · ${subscriptions[i].occurrences} charges seen',
            trailing: formatCurrency(subscriptions[i].averageAmount),
            accent: accent,
          ),
        ],
      ],
    );
  }
}

class _Row extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String trailing;
  final Color accent;

  const _Row({required this.icon, required this.title, required this.subtitle, required this.trailing, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      decoration: solidPanelDecoration(accent: accent),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              shape: BoxShape.circle,
              border: Border.all(color: accent.withValues(alpha: 0.4)),
            ),
            child: Icon(icon, size: 18, color: accent),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall?.copyWith(color: QuorumDarkGround.textPrimary)),
                const SizedBox(height: 2),
                Text(subtitle, style: QuorumMono.detail(context)),
              ],
            ),
          ),
          const SizedBox(width: QuorumSpacing.sm),
          Text(trailing, style: QuorumMono.metricSmall(context, color: QuorumDarkGround.textPrimary)),
        ],
      ),
    );
  }
}
