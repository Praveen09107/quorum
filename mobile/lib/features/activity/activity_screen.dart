// The real Activity screen (`DEC-205`, product rebuild) -- the plan's
// own named "full timeline, grouped by day, filterable by agent /
// outcome / stakes." Reached as a real drill-through from the Log
// tab, matching this rebuild's own established "extend a closely-
// related existing screen" precedent rather than a new bottom-nav
// tab. Every real row here comes from the exact same `GET /honesty_
// log` response the Log tab already fetches once -- this screen
// merges, filters, and groups it differently, it never re-fetches.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/activity/activity_logic.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';
import 'package:quorum_mobile/theme/agent_identity.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class ActivityScreen extends StatefulWidget {
  final HonestyFeedData feed;
  final void Function(LoggedActionData action)? onTapAction;

  const ActivityScreen({super.key, required this.feed, this.onTapAction});

  @override
  State<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends State<ActivityScreen> {
  ActivityFilter _filter = ActivityFilter.none;

  static const _domains = ['email', 'calendar', 'tasks', 'finance', 'career'];
  static const _outcomes = [
    'approved_unchanged',
    'caught_by_gate',
    'corrected_by_user',
    'rejected_by_user',
    'uncertain_no_data',
    'outcome_unknown',
  ];
  static const _stakesTiers = ['S0', 'S1', 'S2', 'S3'];

  @override
  Widget build(BuildContext context) {
    final merged = mergeActivityTimeline(widget.feed);
    final filtered = applyActivityFilter(merged, _filter);
    final groups = groupActivityByDay(filtered);
    final today = DateTime.now();
    final todayKey = DateTime(today.year, today.month, today.day);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Activity'),
        actions: [
          if (_filter.isActive)
            IconButton(
              tooltip: 'Clear filters',
              icon: const Icon(Icons.filter_alt_off_outlined),
              onPressed: () => setState(() => _filter = ActivityFilter.none),
            ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(QuorumSpacing.md),
            child: _FilterBar(
              filter: _filter,
              domains: _domains,
              outcomes: _outcomes,
              stakesTiers: _stakesTiers,
              onChanged: (next) => setState(() => _filter = next),
            ),
          ),
          Expanded(
            child: merged.isEmpty
                ? const Center(child: Text('Nothing real has happened yet.'))
                : filtered.isEmpty
                    ? const Center(child: Text('No real activity matches these filters.'))
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: QuorumSpacing.md),
                        itemCount: groups.length,
                        itemBuilder: (context, index) {
                          final group = groups[index];
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Padding(
                                padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
                                child: Text(
                                  formatActivityDayHeader(group.day, todayKey),
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
                              ),
                              for (final action in group.actions)
                                Card(
                                  child: ListTile(
                                    leading: QuorumIconBadge(
                                      icon: _iconForOutcome(action.outcome),
                                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                                    ),
                                    title: Text(action.description),
                                    subtitle: Text(
                                      '${outcomeLabel(action.outcome)} · ${action.stakes}'
                                      '${action.domain != null ? ' · ${action.domain}' : ''}',
                                    ),
                                    trailing: widget.onTapAction == null ? null : const Icon(Icons.chevron_right),
                                    onTap: widget.onTapAction == null ? null : () => widget.onTapAction!(action),
                                  ),
                                ),
                            ],
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  IconData _iconForOutcome(String outcome) {
    switch (outcome) {
      case 'approved_unchanged':
        return Icons.check_circle_outline;
      case 'caught_by_gate':
        return Icons.shield_outlined;
      case 'corrected_by_user':
        return Icons.edit_outlined;
      case 'rejected_by_user':
        return Icons.block_outlined;
      default:
        return Icons.circle_outlined;
    }
  }
}

class _FilterBar extends StatelessWidget {
  final ActivityFilter filter;
  final List<String> domains;
  final List<String> outcomes;
  final List<String> stakesTiers;
  final void Function(ActivityFilter) onChanged;

  const _FilterBar({
    required this.filter,
    required this.domains,
    required this.outcomes,
    required this.stakesTiers,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final domain in domains) ...[
            _chip(
              label: identityOf(agentForDomain(domain)!).name,
              selected: filter.domain == domain,
              onSelected: (selected) => onChanged(
                ActivityFilter(domain: selected ? domain : null, outcome: filter.outcome, stakes: filter.stakes),
              ),
            ),
            const SizedBox(width: QuorumSpacing.xs),
          ],
          for (final stakes in stakesTiers) ...[
            _chip(
              label: stakes,
              selected: filter.stakes == stakes,
              onSelected: (selected) => onChanged(
                ActivityFilter(domain: filter.domain, outcome: filter.outcome, stakes: selected ? stakes : null),
              ),
            ),
            const SizedBox(width: QuorumSpacing.xs),
          ],
          for (final outcome in outcomes) ...[
            _chip(
              label: outcomeLabel(outcome),
              selected: filter.outcome == outcome,
              onSelected: (selected) => onChanged(
                ActivityFilter(domain: filter.domain, outcome: selected ? outcome : null, stakes: filter.stakes),
              ),
            ),
            const SizedBox(width: QuorumSpacing.xs),
          ],
        ],
      ),
    );
  }

  Widget _chip({required String label, required bool selected, required void Function(bool) onSelected}) {
    return FilterChip(label: Text(label), selected: selected, onSelected: onSelected);
  }
}
