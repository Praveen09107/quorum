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
//
// Phase 8 Session 4 (`DEC-158`): a real, deliberate scope decision, not
// an oversight -- every row's leading icon differs by SHAPE only
// (matching a row's own specific real `outcome`), never by COLOR. Every
// icon badge uses the identical neutral color, section to section, item
// to item. This is a stricter reading of "identical prominence" than
// most of this app's other screens (which do use `QuorumStatusColors`'
// real severity colors freely elsewhere) -- deliberately so here: this
// screen's own header above already made an explicit, reasoned call
// against ANY visual technique that could read as ranking one section's
// real outcome above another's, and a differential status color (green
// for success, red for a catch) would be exactly that kind of technique,
// however truthfully it described any one row. Shape alone conveys the
// real distinction without reintroducing the same asymmetry this
// screen's own `TabBar` rejection already reasoned away once.

import 'package:flutter/material.dart';

import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';
import 'package:quorum_mobile/theme/quorum_theme.dart';
import 'package:quorum_mobile/theme/spacing.dart';

class HonestyLogScreen extends StatelessWidget {
  final HonestyFeedData feed;

  const HonestyLogScreen({super.key, required this.feed});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(QuorumSpacing.md),
      children: [
        Text(
          '${formatSuccessRate(feed.successRate)} of ${feed.total} actions succeeded as drafted',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: QuorumSpacing.md),
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

    final badgeColor = Theme.of(context).colorScheme.onSurfaceVariant;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: QuorumSpacing.sm),
          child: Text(title, style: Theme.of(context).textTheme.titleSmall),
        ),
        for (var i = 0; i < items.length; i++) ...[
          if (i > 0) const SizedBox(height: QuorumSpacing.sm),
          Card(
            child: ListTile(
              leading: QuorumIconBadge(icon: _iconForOutcome(items[i].outcome), color: badgeColor),
              title: Text(items[i].description),
              subtitle: Text(outcomeLabel(items[i].outcome)),
            ),
          ),
        ],
      ],
    );
  }

  /// Icon SHAPE only signals the real, specific outcome -- see file
  /// header for why color deliberately never does, here. `outcome` is a
  /// genuinely open string (no closed contract for it exists), so an
  /// unrecognized value gets a real, honest generic shape rather than
  /// guessing -- the same defensive-open handling `outcomeLabel()`
  /// itself already applies to the identical field.
  IconData _iconForOutcome(String outcome) {
    switch (outcome) {
      case 'approved_unchanged':
        return Icons.check_circle_outline;
      case 'caught_by_gate':
        return Icons.shield_outlined;
      case 'corrected_by_user':
        return Icons.edit_outlined;
      default:
        return Icons.circle_outlined;
    }
  }
}
