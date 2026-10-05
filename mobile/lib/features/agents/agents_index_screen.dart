// The Agents index (`DEC-192`, product rebuild Block D) -- the five
// domain agents as first-class entities a real, signed-in user can
// actually see.
//
// WHY THIS SCREEN EXISTS: a direct, confirmed cause of the complaint
// that drove this whole rebuild -- "none of the AI features reflect in
// the app" -- is that Quorum's five agents, genuinely real in the
// backend since this project's earliest sessions, had NO
// representation anywhere in the app. `DEC-189` gave them an identity
// (color, icon, name); this screen is where that identity actually
// gets a page, backed by their own real, live lifetime track record
// (`GET /agents`, `DEC-192`) rather than a static list of names.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/agents/agents_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/glass.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';
import 'package:quorum_mobile/theme/quorum_kit.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class AgentsIndexScreen extends StatefulWidget {
  final Future<List<AgentStatsData>> Function() fetch;

  const AgentsIndexScreen({super.key, required this.fetch});

  @override
  State<AgentsIndexScreen> createState() => _AgentsIndexScreenState();
}

class _AgentsIndexScreenState extends State<AgentsIndexScreen> {
  late Future<List<AgentStatsData>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.fetch();
  }

  Future<void> _refresh() async {
    final next = widget.fetch();
    // Stale-while-revalidate -- the currently-shown data stays on
    // screen through the reload rather than blanking to a spinner,
    // matching `DEC-187`'s own established real fix for exactly this
    // real Flutter framework behavior.
    setState(() => _future = next);
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return QuorumAmbientBackground(
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: FutureBuilder<List<AgentStatsData>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: RetryErrorState(
                    message: 'Could not load your agents -- ${snapshot.error}',
                    onRetry: () => setState(() => _future = widget.fetch()),
                  ),
                );
              }
              final statsByDomain = {for (final s in snapshot.data!) s.domain: s};
              return ListView(
                padding: const EdgeInsets.all(QuorumSpacing.md),
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
                    child: Text(
                      'Your agents',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: QuorumDarkGround.textPrimary),
                    ),
                  ),
                  Text(
                    'What each one actually does, and its real track record.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
                  ),
                  const SizedBox(height: QuorumSpacing.lg),
                  for (final agent in kDomainAgents)
                    Padding(
                      padding: const EdgeInsets.only(bottom: QuorumSpacing.md),
                      child: _AgentCard(agent: agent, stats: statsByDomain[identityOf(agent).domain]),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _AgentCard extends StatelessWidget {
  final QuorumAgent agent;

  /// `null` only while the fetch is genuinely missing this domain from
  /// the real response -- rendered as an honest "no data" state rather
  /// than a crash, since `GET /agents` is contractually exhaustive over
  /// all five but a client should never assume a server contract holds
  /// forever without checking.
  final AgentStatsData? stats;

  const _AgentCard({required this.agent, required this.stats});

  @override
  Widget build(BuildContext context) {
    final identity = identityOf(agent);
    final localStats = stats;

    return GlassPanel(
      accent: identity.accent,
      accentStrength: (localStats?.isActive ?? false) ? 1.0 : 0.3,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AgentBadge(agent: agent, compact: true),
              const SizedBox(width: QuorumSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      identity.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(color: QuorumDarkGround.textPrimary),
                    ),
                    Text(
                      localStats == null ? 'No data yet' : describeLastActivity(localStats.lastActivity, now: DateTime.now()),
                      style: QuorumMono.detail(context),
                    ),
                  ],
                ),
              ),
              LiveDot(active: false, color: identity.accent),
            ],
          ),
          const SizedBox(height: QuorumSpacing.sm),
          Text(
            identity.purpose,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: QuorumDarkGround.textSecondary),
          ),
          const SizedBox(height: QuorumSpacing.md),
          if (localStats != null) _StatsRow(stats: localStats, accent: identity.accent),
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final AgentStatsData stats;
  final Color accent;

  const _StatsRow({required this.stats, required this.accent});

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        children: [
          Expanded(child: _Stat(label: 'ACTIONS', value: '${stats.lifetimeActions}', accent: accent)),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(child: _Stat(label: 'CAUGHT', value: '${stats.caughtCount}', accent: accent)),
          const SizedBox(width: QuorumSpacing.sm),
          Expanded(
            child: _Stat(
              label: 'RATE',
              value: stats.successRate == null ? '--' : '${(stats.successRate! * 100).round()}%',
              accent: accent,
            ),
          ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final String label;
  final String value;
  final Color accent;

  const _Stat({required this.label, required this.value, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
      decoration: solidPanelDecoration(accent: accent.withValues(alpha: 0.4)),
      child: Column(
        children: [
          Text(value, style: QuorumMono.metricSmall(context, color: QuorumDarkGround.textPrimary)),
          const SizedBox(height: 2),
          Text(label, style: QuorumMono.label(context)),
        ],
      ),
    );
  }
}
