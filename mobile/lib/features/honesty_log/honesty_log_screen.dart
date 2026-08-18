// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against Flutter's documented widget
// API; `flutter analyze` on a real machine is the actual verification.
//
// A real design decision, reasoned through rather than defaulted to the
// obvious pattern: a `TabBar` splitting successes from failures was
// considered and rejected. Even with two visually symmetric tabs, one is
// what a person sees by default and the other is a tap away — not equal
// enough for `build_honesty_feed()`'s explicit "EQUAL prominence, not
// buried" commitment. This screen uses a single scrolling list instead,
// with identical heading style and identical card style for every
// section, in the same order the backend's own response already
// provides them — never reordered to push either one up or down.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

class HonestyLogScreen extends StatelessWidget {
  final HonestyFeedData feed;

  const HonestyLogScreen({super.key, required this.feed});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          '${formatSuccessRate(feed.successRate)} of ${feed.total} actions succeeded as drafted',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 16),
        // Every section below shares identical heading and card styling
        // -- deliberately, per the header comment above.
        _Section(title: 'What went right', items: feed.successes),
        _Section(title: 'What was caught or corrected', items: feed.failuresAndCatches),
        _Section(title: 'Genuinely uncertain', items: feed.genuinelyUncertain),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<LoggedActionData> items;

  const _Section({required this.title, required this.items});

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Text(title, style: Theme.of(context).textTheme.titleSmall),
        ),
        for (final item in items)
          Card(
            child: ListTile(
              title: Text(item.description),
              subtitle: Text(outcomeLabel(item.outcome)),
            ),
          ),
      ],
    );
  }
}
