// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/trust_digest/trust_digest_logic.dart';

class TrustDigestScreen extends StatelessWidget {
  final TrustDigestData digest;

  const TrustDigestScreen({super.key, required this.digest});

  @override
  Widget build(BuildContext context) {
    final delta = formatDelta(digest.delta);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(trendLabel(digest.trend), style: Theme.of(context).textTheme.titleMedium),
        if (delta.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(delta, style: Theme.of(context).textTheme.bodyMedium),
        ],
        const SizedBox(height: 16),
        _WeekRow(label: 'This week', week: digest.currentWeek),
        if (digest.previousWeek != null) _WeekRow(label: 'Last week', week: digest.previousWeek!),
      ],
    );
  }
}

class _WeekRow extends StatelessWidget {
  final String label;
  final WeeklyTrustSummaryData week;

  const _WeekRow({required this.label, required this.week});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(label),
      subtitle: Text('${week.totalActions} actions, ${(week.successRate * 100).round()}% success'),
    );
  }
}
